#!/bin/bash

# --- Setup Error Handling ---

# Exit the script if any command fails.
trap 'echo "Error on line $LINENO"; exit 1' ERR
set -e

# --- Validate Docling installation ---

# Check if Docling CLI is installed and in PATH.
if ! command -v docling &>/dev/null; then
    echo "Error: Docling CLI is not installed or not in PATH"
    exit 1
fi

# --- Input parsing ---

echo "Parsing actor input..."

INPUT="$(apify actor:get-input || {
    echo "Failed to get input"
    exit 1
})"

DOCUMENT_URL="$(echo "${INPUT}" | jq -r '.documentUrl')"
OUTPUT_FORMAT="$(echo "${INPUT}" | jq -r '.outputFormat')"
OUTPUT_NAME="output_file.${OUTPUT_FORMAT}"

# If no document URL is provided, exit with an error.
if [ -z "$DOCUMENT_URL" ]; then
    echo "Error: Missing document URL. Please provide 'documentUrl' in the input"
    exit 1
fi

# If no output format is specified, default to 'md'.
if [ -z "$OUTPUT_FORMAT" ]; then
    OUTPUT_FORMAT="md"
    echo "No output format specified. Defaulting to 'md'"
fi

# Validate the output format.
case "$OUTPUT_FORMAT" in md | json | html | text | doctags) ;;
*)
    echo "Error: Invalid output format '$OUTPUT_FORMAT'. Supported formats are 'md', 'json', 'html', 'text', and 'doctags'"
    exit 1
    ;;
esac

# --- Build Docling command ---

DOC_CONVERT_CMD="docling --verbose \"${DOCUMENT_URL}\" --to \"${OUTPUT_FORMAT}\""

# If OCR is enabled, add the OCR flag to the command.
if [ "$(echo "${INPUT}" | jq -r '.ocr')" = "true" ]; then
    DOC_CONVERT_CMD="${DOC_CONVERT_CMD} --ocr"
fi

# --- Process document with Docling ---

echo "Processing document with Docling CLI..."
echo "Running: $DOC_CONVERT_CMD"

# Create a timestamp file to ensure the document is processed only once.
touch docling.timestamp || {
    echo "Error: Failed to create timestamp file"
    exit 1
}

# Execute the command and capture both stdout and stderr.
eval "$DOC_CONVERT_CMD" >docling.log 2>&1 || {
    cat docling.log
    echo "Error: Docling command failed"
    exit 1
}

GENERATED_FILE="$(find . -type f -name "*.${OUTPUT_FORMAT}" -newer docling.timestamp)"

# If no generated file is found, exit with an error.
if [ -z "$GENERATED_FILE" ]; then
    echo "Error: Could not find generated output file with extension .$OUTPUT_FORMAT"
    exit 1
fi

mv "${GENERATED_FILE}" "${OUTPUT_NAME}"

# --- Validate output ---

# If the output file is not found, exit with an error.
if [ ! -f "$OUTPUT_NAME" ]; then
    echo "Error: Expected output file '$OUTPUT_NAME' was not generated"
    exit 1
fi

# If the output file is empty, exit with an error.
if [ ! -s "$OUTPUT_NAME" ]; then
    echo "Error: Generated output file '$OUTPUT_NAME' is empty"
    exit 1
fi

echo "Document successfully processed and exported as '$OUTPUT_FORMAT' to file: $OUTPUT_NAME"

# --- Store output and log in Key-Value Store ---

echo "Pushing processed document to Key-Value Store (record key: OUTPUT_RESULT)..."
apify actor:set-value "OUTPUT_RESULT" --contentType "application/$OUTPUT_FORMAT" <"$OUTPUT_NAME" || {
    echo "Error: Failed to push the output document to the Key-Value Store"
    exit 1
}

if [ -f "docling.log" ]; then
    if [ -s "docling.log" ]; then
        echo "Log file is not empty, pushing to Key-Value Store (record key: DOCLING_LOG)..."
        apify actor:set-value "DOCLING_LOG" --contentType "text/plain" <"docling.log" || {
            echo "Warning: Failed to push the log file to the Key-Value Store"
        }
    else
        echo "Warning: docling.log file exists but is empty"
    fi
else
    echo "Warning: No docling.log file found"
fi

# --- Cleanup temporary files ---

cleanup() {
    local exit_code=$?
    rm -f docling.timestamp docling.log || true
    exit $exit_code
}

trap cleanup EXIT

echo "Done!"
