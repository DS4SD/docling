#!/bin/bash

# --- Setup Error Handling ---

# Initialize log file first.
LOG_FILE="/tmp/docling.log"
touch "$LOG_FILE" || {
    echo "Fatal: Cannot create log file at $LOG_FILE"
    exit 1
}

# Ensure all output is logged.
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

# Exit the script if any command fails.
trap 'echo "Error on line $LINENO"' ERR
set -e

# --- Define error codes ---

readonly ERR_INVALID_INPUT=10
readonly ERR_URL_INACCESSIBLE=11
readonly ERR_DOCLING_FAILED=12
readonly ERR_OUTPUT_MISSING=13
readonly ERR_STORAGE_FAILED=14

# --- Input parsing ---

echo "Parsing actor input..."

INPUT="$(apify actor:get-input || {
    echo "Failed to get input"
    exit 1
})"

DOCUMENT_URL="$(echo "${INPUT}" | jq -r '.documentUrl')"
OUTPUT_FORMAT="$(echo "${INPUT}" | jq -r '.outputFormat')"
OCR_ENABLED="$(echo "${INPUT}" | jq -r '.ocr')"

# If no output format is specified, default to 'md'.
if [ -z "$OUTPUT_FORMAT" ] || [ "$OUTPUT_FORMAT" = "null" ]; then
    OUTPUT_FORMAT="md"
    echo "No output format specified. Defaulting to 'md'"
fi

# Validate the output format.
case "$OUTPUT_FORMAT" in md | json | html | text | doctags) ;;
*)
    echo "Error: Invalid output format '$OUTPUT_FORMAT'. Supported formats are 'md', 'json', 'html', 'text', and 'doctags'"
    apify actor:push-data "{\"url\": \"${DOCUMENT_URL}\", \"status\": \"error\", \"error\": \"Invalid output format\"}" || true
    exit $ERR_INVALID_INPUT
    ;;
esac

# Set output filename based on format.
OUTPUT_NAME="output_file.${OUTPUT_FORMAT}"

if [ -z "$DOCUMENT_URL" ] || [ "$DOCUMENT_URL" = "null" ]; then
    echo "Error: Missing document URL. Please provide 'documentUrl' in the input"
    apify actor:push-data "{\"status\": \"error\", \"error\": \"Missing document URL\"}" || true
    exit $ERR_INVALID_INPUT
fi

# Validate URL is accessible.
echo "Validating document URL..."
if ! curl --output /dev/null --silent --head --fail "${DOCUMENT_URL}"; then
    echo "Error: Unable to access document at URL: ${DOCUMENT_URL}"
    echo "Please ensure the URL is valid and publicly accessible."
    apify actor:push-data "{\"url\": \"${DOCUMENT_URL}\", \"status\": \"error\", \"error\": \"URL inaccessible\"}" || true
    exit $ERR_URL_INACCESSIBLE
fi

# --- Create JSON payload for docling-serve API ---

echo "Creating API request for docling-serve..."

# Set OCR flag.
if [ "$OCR_ENABLED" = "true" ]; then
    OCR_VALUE="true"
else
    OCR_VALUE="false"
fi

# Create a temporary file for the JSON payload.
REQUEST_FILE="/tmp/docling_request.json"
cat > "$REQUEST_FILE" << EOF
{
    "document_url": "${DOCUMENT_URL}",
    "output_format": "${OUTPUT_FORMAT}",
    "ocr": ${OCR_VALUE}
}
EOF

echo "Request payload:"
cat "$REQUEST_FILE"

# --- Call docling-serve API ---

echo "Calling docling-serve API (localhost:8080/convert)..."

RESPONSE_FILE="/tmp/docling_response.json"
HTTP_CODE=$(curl -s -o "$RESPONSE_FILE" -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d @"$REQUEST_FILE" \
    http://localhost:8080/convert)

echo "API Response Status Code: $HTTP_CODE"

# Check response status code.
if [ "$HTTP_CODE" -ne 200 ]; then
    echo "Error: docling-serve API returned error code $HTTP_CODE"
    if [ -f "$RESPONSE_FILE" ]; then
        echo "Error response:"
        cat "$RESPONSE_FILE"
    fi

    ERROR_MSG=$(jq -r '.error // "Unknown API error"' "$RESPONSE_FILE" 2>/dev/null || echo "Unknown API error")

    apify actor:push-data "{\"url\": \"${DOCUMENT_URL}\", \"status\": \"error\", \"error\": \"${ERROR_MSG}\"}" || true
    exit $ERR_DOCLING_FAILED
fi

# --- Process API response ---

echo "Processing API response..."

# Extract content from response and save to output file.
if ! jq -r '.content' "$RESPONSE_FILE" > "$OUTPUT_NAME" 2>/dev/null; then
    echo "Error: Failed to parse API response or extract content"
    echo "Response content:"
    cat "$RESPONSE_FILE"

    apify actor:push-data "{\"url\": \"${DOCUMENT_URL}\", \"status\": \"error\", \"error\": \"Failed to parse API response\"}" || true
    exit $ERR_OUTPUT_MISSING
fi

# Validate output file.
if [ ! -f "$OUTPUT_NAME" ]; then
    echo "Error: Output file was not created"
    apify actor:push-data "{\"url\": \"${DOCUMENT_URL}\", \"status\": \"error\", \"error\": \"Output file not created\"}" || true
    exit $ERR_OUTPUT_MISSING
fi

# Validate output file is not empty.
if [ ! -s "$OUTPUT_NAME" ]; then
    echo "Error: Output file is empty"
    apify actor:push-data "{\"url\": \"${DOCUMENT_URL}\", \"status\": \"error\", \"error\": \"Output file is empty\"}" || true
    exit $ERR_OUTPUT_MISSING
fi

echo "Document successfully processed and exported as '$OUTPUT_FORMAT' to file: $OUTPUT_NAME"

# --- Store output and log in key-value store ---

echo "Pushing processed document to key-value store (record key: OUTPUT_RESULT)..."

CONTENT_TYPE=""
case "$OUTPUT_FORMAT" in
    md)      CONTENT_TYPE="text/markdown" ;;
    json)    CONTENT_TYPE="application/json" ;;
    html)    CONTENT_TYPE="text/html" ;;
    text)    CONTENT_TYPE="text/plain" ;;
    doctags) CONTENT_TYPE="application/json" ;;
    *)       CONTENT_TYPE="text/plain" ;;
esac

apify actor:set-value "OUTPUT_RESULT" --contentType "$CONTENT_TYPE" < "$OUTPUT_NAME" || {
    echo "Error: Failed to push the output document to the key-value store"
    exit $ERR_STORAGE_FAILED
}

# Create dataset record with processing results.
RESULT_URL="https://api.apify.com/v2/key-value-stores/${APIFY_DEFAULT_KEY_VALUE_STORE_ID}/records/OUTPUT_RESULT"
echo "Adding record to dataset..."
apify actor:push-data "{\"url\": \"${DOCUMENT_URL}\", \"output_file\": \"${RESULT_URL}\", \"status\": \"success\"}" || {
    echo "Warning: Failed to push data to dataset"
}

# Store logs.
if [ -f "$LOG_FILE" ] && [ -s "$LOG_FILE" ]; then
    echo "Pushing log file to key-value store (record key: DOCLING_LOG)..."
    apify actor:set-value "DOCLING_LOG" --contentType "text/plain" < "$LOG_FILE" || {
        echo "Warning: Failed to push the log file to the key-value store"
    }
fi

# --- Cleanup temporary files ---

cleanup() {
    local exit_code=$?
    rm -f "$REQUEST_FILE" "$RESPONSE_FILE" || true
    exit $exit_code
}

trap cleanup EXIT

echo "Processing completed successfully!"
echo "You can find your results at: ${RESULT_URL}"
