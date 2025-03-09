#!/bin/bash

# Function to upload content to the key-value store
upload_to_kvs() {
    local content_file="$1"
    local key_name="$2"
    local content_type="$3"
    local description="$4"

    # Find the Apify CLI command
    local apify_cmd=""
    for cmd in "apify" "actor" "/usr/local/bin/apify" "/usr/bin/apify" "/opt/apify/cli/bin/apify"; do
        if command -v "$cmd" &> /dev/null; then
            apify_cmd="$cmd"
            break
        fi
    done

    if [ -n "$apify_cmd" ]; then
        echo "Uploading $description to key-value store (key: $key_name)..."

        # Create a temporary home directory with write permissions
        export TMPDIR="/tmp/apify-home-${RANDOM}"
        mkdir -p "$TMPDIR"

        # Multiple strategies to disable version checking
        export APIFY_DISABLE_VERSION_CHECK=1
        export NODE_OPTIONS="--no-warnings"
        export HOME="$TMPDIR"  # Override home directory to writable location

        # Use the --no-update-notifier flag if available
        if $apify_cmd --help | grep -q "\--no-update-notifier"; then
            if $apify_cmd --no-update-notifier actor:set-value "$key_name" --contentType "$content_type" < "$content_file"; then
                echo "Successfully uploaded $description to key-value store"
                local url="https://api.apify.com/v2/key-value-stores/${APIFY_DEFAULT_KEY_VALUE_STORE_ID}/records/$key_name"
                echo "$description available at: $url"
                rm -rf "$TMPDIR" 2>/dev/null || true  # Clean up temp dir
                return 0
            fi
        else
            # Fall back to regular command if flag isn't available
            if $apify_cmd actor:set-value "$key_name" --contentType "$content_type" < "$content_file"; then
                echo "Successfully uploaded $description to key-value store"
                local url="https://api.apify.com/v2/key-value-stores/${APIFY_DEFAULT_KEY_VALUE_STORE_ID}/records/$key_name"
                echo "$description available at: $url"
                rm -rf "$TMPDIR" 2>/dev/null || true  # Clean up temp dir
                return 0
            fi
        fi

        echo "ERROR: Failed to upload $description to key-value store"
        rm -rf "$TMPDIR" 2>/dev/null || true  # Clean up temp dir
        return 1
    else
        echo "ERROR: Apify CLI not found for $description upload"
        return 1
    fi
}


# --- Setup logging and error handling ---

LOG_FILE="/tmp/docling.log"
touch "$LOG_FILE" || {
    echo "Fatal: Cannot create log file at $LOG_FILE"
    exit 1
}

# Log to both console and file
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

# Exit codes
readonly ERR_API_UNAVAILABLE=15
readonly ERR_INVALID_INPUT=16


# --- Debug environment ---

echo "Date: $(date)"
echo "Python version: $(python --version 2>&1)"
echo "Docling-serve path: $(which docling-serve 2>/dev/null || echo 'Not found')"
echo "Working directory: $(pwd)"


# --- Setup tools ---

echo "Setting up tools..."
TOOLS_DIR="/tmp/docling-tools"
mkdir -p "$TOOLS_DIR"

# Copy tools if available
if [ -d "/build-files" ]; then
    echo "Copying tools from /build-files..."
    cp -r /build-files/* "$TOOLS_DIR/"
    export PATH="$TOOLS_DIR/bin:$PATH"
else
    echo "Warning: No build files directory found. Some tools may be unavailable."
fi

# Check OCR directories and ensure they're writable
echo "Checking OCR directory permissions..."
OCR_DIR="/opt/app-root/src/.EasyOCR"
if [ -d "$OCR_DIR" ]; then
    # Test if we can write to the directory
    if touch "$OCR_DIR/test_write" 2>/dev/null; then
        echo "[✓] OCR directory is writable"
        rm "$OCR_DIR/test_write"
    else
        echo "[✗] OCR directory is not writable, setting up alternative in /tmp"
        # Create alternative in /tmp (which is writable)
        mkdir -p "/tmp/.EasyOCR/user_network"
        export EASYOCR_MODULE_PATH="/tmp/.EasyOCR"
    fi
else
    echo "OCR directory not found, creating in /tmp"
    mkdir -p "/tmp/.EasyOCR/user_network"
    export EASYOCR_MODULE_PATH="/tmp/.EasyOCR"
fi


# --- Starting the API ---

echo "Starting docling-serve API..."

# Create a dedicated working directory in /tmp (writable)
API_DIR="/tmp/docling-api"
mkdir -p "$API_DIR"
cd "$API_DIR"
echo "API working directory: $(pwd)"

# Find docling-serve executable
DOCLING_SERVE_PATH=$(which docling-serve)
echo "Docling-serve executable: $DOCLING_SERVE_PATH"

# Start the API with minimal parameters to avoid any issues
echo "Starting docling-serve API..."
"$DOCLING_SERVE_PATH" run --host 0.0.0.0 --port 5001 > "$API_DIR/docling-serve.log" 2>&1 &
API_PID=$!
echo "Started docling-serve API with PID: $API_PID"

# A more reliable wait for API startup
echo "Waiting for API to initialize..."
MAX_TRIES=30
tries=0
started=false

while [ $tries -lt $MAX_TRIES ]; do
    tries=$((tries + 1))

    # Check if process is still running
    if ! ps -p $API_PID > /dev/null; then
        echo "ERROR: docling-serve API process terminated unexpectedly after $tries seconds"
        break
    fi

    # Check log for startup completion or errors
    if grep -q "Application startup complete" "$API_DIR/docling-serve.log" 2>/dev/null; then
        echo "[✓] API startup completed successfully after $tries seconds"
        started=true
        break
    fi

    if grep -q "Permission denied\|PermissionError" "$API_DIR/docling-serve.log" 2>/dev/null; then
        echo "ERROR: Permission errors detected in API startup"
        break
    fi

    # Sleep and check again
    sleep 1

    # Output a progress indicator every 5 seconds
    if [ $((tries % 5)) -eq 0 ]; then
        echo "Still waiting for API startup... ($tries/$MAX_TRIES seconds)"
    fi
done

# Show log content regardless of outcome
echo "docling-serve log output so far:"
tail -n 20 "$API_DIR/docling-serve.log"

# Verify the API is running
if ! ps -p $API_PID > /dev/null; then
    echo "ERROR: docling-serve API failed to start"
    if [ -f "$API_DIR/docling-serve.log" ]; then
        echo "Full log output:"
        cat "$API_DIR/docling-serve.log"
    fi
    exit $ERR_API_UNAVAILABLE
fi

if [ "$started" != "true" ]; then
    echo "WARNING: API process is running but startup completion was not detected"
    echo "Will attempt to continue anyway..."
fi

# Try to verify API is responding at this point
echo "Verifying API responsiveness..."
(python -c "
import sys, time, socket
for i in range(5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(('localhost', 5001))
        if result == 0:
            s.close()
            print('Port 5001 is open and accepting connections')
            sys.exit(0)
        s.close()
    except Exception as e:
        pass
    time.sleep(1)
print('Could not connect to API port after 5 attempts')
sys.exit(1)
" && echo "API verification succeeded") || echo "API verification failed, but continuing anyway"

# Define API endpoint
DOCLING_API_ENDPOINT="http://localhost:5001/v1alpha/convert/source"


# --- Processing document ---

echo "Starting document processing..."
echo "Reading input from Apify..."

INPUT=""

# Create directory if it doesn't exist
mkdir -p "/tmp/actor-input" || echo "Warning: Could not create /tmp/actor-input directory"

# List all possible input locations for debugging
echo "Listing potential input file locations:"
ls -la "/tmp/actor-input/" 2>/dev/null || echo "Cannot list /tmp/actor-input/"
ls -la "/input/" 2>/dev/null || echo "Cannot list /input/"

# Check multiple potential locations for input file
if [ -f "/tmp/actor-input/INPUT" ]; then
    echo "Found standard Actor input file at /tmp/actor-input/INPUT"
    echo "Content:"
    cat "/tmp/actor-input/INPUT"
    INPUT=$(cat "/tmp/actor-input/INPUT")
elif [ -f "/input/INPUT" ]; then
    echo "Found Actor input file at /input/INPUT"
    echo "Content:"
    cat "/input/INPUT"
    INPUT=$(cat "/input/INPUT")
# Fallback to environment variable
elif [ -n "$APIFY_INPUT_JSON" ]; then
    echo "Using APIFY_INPUT_JSON environment variable"
    INPUT="$APIFY_INPUT_JSON"
# Last resort: use test input - now defaulting to md as requested
else
    echo "No input found, using test input with md format"
    TEST_INPUT='{"documentUrl":"https://vancura.dev/assets/actor-test/facial-hairstyles-and-filtering-facepiece-respirators.pdf","ocr":true,"outputFormat":"md"}'
    mkdir -p "/tmp/actor-input"
    echo "$TEST_INPUT" > "/tmp/actor-input/INPUT"
    INPUT="$TEST_INPUT"
fi

echo "Input content: $INPUT"

# Extract values from INPUT using Python
echo "Using Python to parse input..."
DOCUMENT_URL="$(echo "$INPUT" | python -c "import sys, json; print(json.load(sys.stdin).get('documentUrl', ''))")"
OUTPUT_FORMAT="$(echo "$INPUT" | python -c "import sys, json; print(json.load(sys.stdin).get('outputFormat', 'md'))")"
OCR_ENABLED="$(echo "$INPUT" | python -c "import sys, json; print(str(json.load(sys.stdin).get('ocr', True)).lower())")"

# Validate input schema should already enforce this, but double-check
if [ -z "$DOCUMENT_URL" ]; then
    echo "ERROR: No document URL provided in input"

    # Try to push data to Actor but don't exit if it fails
    if command -v actor &> /dev/null; then
        echo "Reporting missing document URL to Actor storage..."
        if actor push-data "{\"status\": \"error\", \"error\": \"No document URL provided in input\"}" 2>&1; then
            echo "Successfully pushed error message to Actor storage"
        else
            echo "Warning: Failed to push error message to Actor storage"
        fi
    fi

    # Use default document URL for testing instead of exiting
    echo "Using a default document URL for testing: https://arxiv.org/pdf/2408.09869"
    DOCUMENT_URL="https://arxiv.org/pdf/2408.09869"
fi

if [ -z "$OUTPUT_FORMAT" ]; then
    echo "No output format specified, defaulting to 'md'"
    OUTPUT_FORMAT="md"
fi

echo "Input values: documentUrl=$DOCUMENT_URL, outputFormat=$OUTPUT_FORMAT, ocr=$OCR_ENABLED"

# Create the request JSON
REQUEST_JSON="{\"options\":{\"to_formats\":[\"$OUTPUT_FORMAT\"],\"ocr\":$OCR_ENABLED},\"http_sources\":[{\"url\":\"$DOCUMENT_URL\"}]}"
echo "$REQUEST_JSON" > "$API_DIR/request.json"

# Send the conversion request
echo "Sending conversion request to docling-serve API..."
python -c "
import json
import time
import sys
import os
import traceback

try:
    # Load request data from temporary location
    with open('$API_DIR/request.json', 'r') as f:
        request_data = json.load(f)

    print(f'Request to convert URL: {request_data[\"http_sources\"][0][\"url\"]}')
    print(f'Output format: {request_data[\"options\"][\"to_formats\"][0]}')
    print(f'OCR enabled: {request_data[\"options\"][\"ocr\"]}')

    # Try requests first, fall back to urllib
    try:
        import requests
        print('Using requests library for API call')

        # Record start time for timing
        start_time = time.time()
        print(f'Starting conversion request at {time.strftime(\"%H:%M:%S\")}')

        response = requests.post(
            '$DOCLING_API_ENDPOINT',
            json=request_data,
            timeout=300  # 5 minutes timeout
        )

        elapsed = time.time() - start_time
        print(f'Conversion request completed in {elapsed:.2f} seconds')
        print(f'Response status code: {response.status_code}')

        # Save the full response for debugging
        with open('$API_DIR/full_response.txt', 'w') as f:
            f.write(f'Status code: {response.status_code}\\n')
            f.write(f'Headers: {response.headers}\\n\\n')
            f.write(f'Content: {response.text[:10000]}...' if len(response.text) > 10000 else f'Content: {response.text}')

        if response.status_code == 200:
            with open('$API_DIR/response.json', 'w') as f:
                f.write(response.text)

            # Parse the response even if it's not valid JSON
            try:
                resp_data = response.json()
                print('Successfully parsed response as JSON')

                # Save detailed diagnostics about the response structure
                with open('$API_DIR/response_structure.txt', 'w') as f:
                    f.write(f'Response keys: {list(resp_data.keys())}\\n')
                    if 'document' in resp_data:
                        f.write(f'Document keys: {list(resp_data[\"document\"].keys() if resp_data[\"document\"] else [])}\\n')

                        # Check for specific content fields with null safety
                        doc = resp_data['document'] or {}
                        if 'html_content' in doc and doc['html_content']:
                            f.write(f'HTML content length: {len(doc[\"html_content\"])}\\n')
                        elif 'html_content' in doc:
                            f.write('HTML content is present but empty or null\\n')

                        if 'md_content' in doc and doc['md_content']:
                            f.write(f'Markdown content length: {len(doc[\"md_content\"])}\\n')
                        elif 'md_content' in doc:
                            f.write('Markdown content is present but empty or null\\n')

                        if 'text_content' in doc and doc['text_content']:
                            f.write(f'Text content length: {len(doc[\"text_content\"])}\\n')
                        elif 'text_content' in doc:
                            f.write('Text content is present but empty or null\\n')

                        if 'json_content' in doc and doc['json_content']:
                            f.write(f'JSON content length: {len(doc[\"json_content\"])}\\n')
                        elif 'json_content' in doc:
                            f.write('JSON content is present but empty or null\\n')

                    if 'outputs' in resp_data:
                        f.write(f'Outputs count: {len(resp_data[\"outputs\"])}\\n')
                        if resp_data['outputs']:
                            f.write(f'First output keys: {list(resp_data[\"outputs\"][0].keys())}\\n')
                            if 'files' in resp_data['outputs'][0]:
                                f.write(f'Files count: {len(resp_data[\"outputs\"][0][\"files\"])}\\n')
                                if resp_data['outputs'][0]['files']:
                                    f.write(f'First file keys: {list(resp_data[\"outputs\"][0][\"files\"][0].keys())}\\n')
                                    if 'content' in resp_data['outputs'][0]['files'][0]:
                                        content_length = len(resp_data['outputs'][0]['files'][0]['content'])
                                        f.write(f'Content length: {content_length}\\n')

                # Process the response - check for outputs and files
                if 'outputs' in resp_data and resp_data['outputs']:
                    output = resp_data['outputs'][0]
                    print(f'Found {len(resp_data[\"outputs\"])} outputs in response')

                    if 'files' in output and output['files']:
                        file_data = output['files'][0]
                        print(f'Found {len(output[\"files\"])} files in output')

                        if 'content' in file_data and file_data['content']:
                            print(f'Found content in file (length: {len(file_data[\"content\"])})')
                            with open('$API_DIR/output.$OUTPUT_FORMAT', 'w') as f:
                                f.write(file_data['content'])
                            print('CONVERSION SUCCESS')
                            sys.exit(0)
                        else:
                            if 'content' in file_data:
                                print('Content field exists but is empty')
                            else:
                                print('No content field in file data')
                                print(f'Available fields: {list(file_data.keys())}')
                    else:
                        print('No files found in output')
                        print(f'Available fields: {list(output.keys())}')

                # Alternative response format check - document field
                elif 'document' in resp_data and resp_data['status'] == 'success':
                    print('Found alternative response format with document field')
                    document = resp_data['document'] or {}

                    # Check format fields in document to see what's available
                    available_formats = []
                    if 'html_content' in document and document['html_content']:
                        available_formats.append(('html', document['html_content']))
                    if 'md_content' in document and document['md_content']:
                        available_formats.append(('md', document['md_content']))
                    if 'text_content' in document and document['text_content']:
                        available_formats.append(('text', document['text_content']))
                    if 'json_content' in document and document['json_content']:
                        available_formats.append(('json', document['json_content']))

                    if available_formats:
                        print(f'Found {len(available_formats)} available formats: {[f[0] for f in available_formats]}')

                        # First try to find the exact requested format
                        requested_format_match = next((f for f in available_formats if f[0] == '$OUTPUT_FORMAT'.lower()), None)

                        if requested_format_match:
                            format_type, content = requested_format_match
                            print(f'Found content in requested format {format_type} (length: {len(content)})')
                        else:
                            # If requested format not found, use the first available
                            format_type, content = available_formats[0]
                            print(f'Requested format not found, using alternative format {format_type} (length: {len(content)})')

                        # Save the content to the output file with appropriate extension
                        with open(f'$API_DIR/output.{format_type}', 'w') as f:
                            f.write(content)

                        # If we're using a different format than requested, also save with requested extension
                        if format_type != '$OUTPUT_FORMAT'.lower():
                            print(f'Saving content with requested extension {format_type} -> $OUTPUT_FORMAT')
                            with open('$API_DIR/output.$OUTPUT_FORMAT', 'w') as f:
                                f.write(content)

                        print('CONVERSION SUCCESS')
                        sys.exit(0)
                    else:
                        # No content fields found or all are empty
                        # Check if fields exist but are empty or null
                        empty_fields = []
                        if 'html_content' in document and not document['html_content']:
                            empty_fields.append('html_content')
                        if 'md_content' in document and not document['md_content']:
                            empty_fields.append('md_content')
                        if 'text_content' in document and not document['text_content']:
                            empty_fields.append('text_content')

                        if empty_fields:
                            print(f'Found content fields but they are empty or null: {empty_fields}')
                        else:
                            print('No content fields found in document')

                        print(f'Available fields in document: {list(document.keys() if document else [])}')
                else:
                    print('No outputs found in response')
                    print(f'Available fields: {list(resp_data.keys())}')

                # Try to extract any alternate formats or metadata
                if 'metadata' in resp_data:
                    print('Metadata found in response, saving to file')
                    with open('$API_DIR/metadata.json', 'w') as f:
                        json.dump(resp_data['metadata'], f, indent=2)

                print('CONVERSION PARTIAL - Some data available but not complete')
            except Exception as json_error:
                print(f'Failed to parse response as JSON: {json_error}')
                traceback.print_exc()

                # Save raw content as text if JSON parsing fails
                with open('$API_DIR/output.txt', 'w') as f:
                    f.write(response.text)
                print('Saved raw response as text file')
                print('CONVERSION PARTIAL - Raw response saved')
        else:
            print(f'Error response: {response.text[:500]}')
            print('CONVERSION FAILED')

    except ImportError:
        # Fall back to urllib
        import urllib.request
        import urllib.error

        print('Using urllib library for API call')
        headers = {'Content-Type': 'application/json'}
        req_data = json.dumps(request_data).encode('utf-8')

        req = urllib.request.Request(
            '$DOCLING_API_ENDPOINT',
            data=req_data,
            headers=headers,
            method='POST'
        )

        try:
            start_time = time.time()
            print(f'Starting conversion request at {time.strftime(\"%H:%M:%S\")}')

            with urllib.request.urlopen(req, timeout=300) as response:
                elapsed = time.time() - start_time
                print(f'Conversion request completed in {elapsed:.2f} seconds')
                print(f'Response status: {response.status}')

                if response.status == 200:
                    response_text = response.read().decode('utf-8')

                    # Save full response for debugging
                    with open('$API_DIR/full_response.txt', 'w') as f:
                        f.write(f'Status: {response.status}\\n')
                        f.write(f'Headers: {response.headers}\\n\\n')
                        f.write(f'Content: {response_text[:10000]}...' if len(response_text) > 10000 else f'Content: {response_text}')

                    with open('$API_DIR/response.json', 'w') as f:
                        f.write(response_text)

                    try:
                        resp_data = json.loads(response_text)
                        print('Successfully parsed response as JSON')

                        # Save detailed diagnostics about the response structure
                        with open('$API_DIR/response_structure.txt', 'w') as f:
                            f.write(f'Response keys: {list(resp_data.keys())}\\n')
                            if 'document' in resp_data:
                                f.write(f'Document keys: {list(resp_data[\"document\"].keys() if resp_data[\"document\"] else [])}\\n')

                                # Check for specific content fields with null safety
                                doc = resp_data['document'] or {}
                                if 'html_content' in doc and doc['html_content']:
                                    f.write(f'HTML content length: {len(doc[\"html_content\"])}\\n')
                                elif 'html_content' in doc:
                                    f.write('HTML content is present but empty or null\\n')

                                if 'md_content' in doc and doc['md_content']:
                                    f.write(f'Markdown content length: {len(doc[\"md_content\"])}\\n')
                                elif 'md_content' in doc:
                                    f.write('Markdown content is present but empty or null\\n')

                                if 'text_content' in doc and doc['text_content']:
                                    f.write(f'Text content length: {len(doc[\"text_content\"])}\\n')
                                elif 'text_content' in doc:
                                    f.write('Text content is present but empty or null\\n')

                                if 'json_content' in doc and doc['json_content']:
                                    f.write(f'JSON content length: {len(doc[\"json_content\"])}\\n')
                                elif 'json_content' in doc:
                                    f.write('JSON content is present but empty or null\\n')

                            if 'outputs' in resp_data:
                                f.write(f'Outputs count: {len(resp_data[\"outputs\"])}\\n')
                                if resp_data['outputs']:
                                    f.write(f'First output keys: {list(resp_data[\"outputs\"][0].keys())}\\n')
                                    if 'files' in resp_data['outputs'][0]:
                                        f.write(f'Files count: {len(resp_data[\"outputs\"][0][\"files\"])}\\n')
                                        if resp_data['outputs'][0]['files']:
                                            f.write(f'First file keys: {list(resp_data[\"outputs\"][0][\"files\"][0].keys())}\\n')
                                            if 'content' in resp_data['outputs'][0]['files'][0]:
                                                content_length = len(resp_data['outputs'][0]['files'][0]['content'])
                                                f.write(f'Content length: {content_length}\\n')

                        if 'outputs' in resp_data and resp_data['outputs']:
                            output = resp_data['outputs'][0]
                            print(f'Found {len(resp_data[\"outputs\"])} outputs in response')

                            if 'files' in output and output['files']:
                                file_data = output['files'][0]
                                print(f'Found {len(output[\"files\"])} files in output')

                                if 'content' in file_data and file_data['content']:
                                    print(f'Found content in file (length: {len(file_data[\"content\"])})')
                                    with open('$API_DIR/output.$OUTPUT_FORMAT', 'w') as f:
                                        f.write(file_data['content'])
                                    print('CONVERSION SUCCESS')
                                    sys.exit(0)
                                else:
                                    if 'content' in file_data:
                                        print('Content field exists but is empty')
                                    else:
                                        print('No content field in file data')
                                        print(f'Available fields: {list(file_data.keys())}')
                            else:
                                print('No files found in output')
                                print(f'Available fields: {list(output.keys())}')

                        # Alternative response format check - document field
                        elif 'document' in resp_data and resp_data['status'] == 'success':
                            print('Found alternative response format with document field')
                            document = resp_data['document'] or {}

                            # Check format fields in document to see what's available
                            available_formats = []
                            if 'html_content' in document and document['html_content']:
                                available_formats.append(('html', document['html_content']))
                            if 'md_content' in document and document['md_content']:
                                available_formats.append(('md', document['md_content']))
                            if 'text_content' in document and document['text_content']:
                                available_formats.append(('text', document['text_content']))
                            if 'json_content' in document and document['json_content']:
                                available_formats.append(('json', document['json_content']))

                            if available_formats:
                                print(f'Found {len(available_formats)} available formats: {[f[0] for f in available_formats]}')

                                # First try to find the exact requested format
                                requested_format_match = next((f for f in available_formats if f[0] == '$OUTPUT_FORMAT'.lower()), None)

                                if requested_format_match:
                                    format_type, content = requested_format_match
                                    print(f'Found content in requested format {format_type} (length: {len(content)})')
                                else:
                                    # If requested format not found, use the first available
                                    format_type, content = available_formats[0]
                                    print(f'Requested format not found, using alternative format {format_type} (length: {len(content)})')

                                # Save the content to the output file with appropriate extension
                                with open(f'$API_DIR/output.{format_type}', 'w') as f:
                                    f.write(content)

                                # If we're using a different format than requested, also save with requested extension
                                if format_type != '$OUTPUT_FORMAT'.lower():
                                    print(f'Saving content with requested extension {format_type} -> $OUTPUT_FORMAT')
                                    with open('$API_DIR/output.$OUTPUT_FORMAT', 'w') as f:
                                        f.write(content)

                                print('CONVERSION SUCCESS')
                                sys.exit(0)
                            else:
                                # No content fields found or all are empty
                                # Check if fields exist but are empty or null
                                empty_fields = []
                                if 'html_content' in document and not document['html_content']:
                                    empty_fields.append('html_content')
                                if 'md_content' in document and not document['md_content']:
                                    empty_fields.append('md_content')
                                if 'text_content' in document and not document['text_content']:
                                    empty_fields.append('text_content')

                                if empty_fields:
                                    print(f'Found content fields but they are empty or null: {empty_fields}')
                                else:
                                    print('No content fields found in document')

                                print(f'Available fields in document: {list(document.keys() if document else [])}')
                        else:
                            print('No outputs found in response')
                            print(f'Available fields: {list(resp_data.keys())}')

                        print('CONVERSION PARTIAL - Some data available but not complete')
                    except Exception as json_error:
                        print(f'Failed to parse response as JSON: {json_error}')
                        traceback.print_exc()

                        # Save raw content as text if JSON parsing fails
                        with open('$API_DIR/output.txt', 'w') as f:
                            f.write(response_text)
                        print('Saved raw response as text file')
                        print('CONVERSION PARTIAL - Raw response saved')
                else:
                    print(f'Error status: {response.status}')
                    print('CONVERSION FAILED')
        except urllib.error.HTTPError as e:
            print(f'HTTP Error: {e.code} - {e.reason}')
            print(f'Response body: {e.read().decode(\"utf-8\")[:500]}')
            print('CONVERSION FAILED')
        except urllib.error.URLError as e:
            print(f'URL Error: {e.reason}')
            print('CONVERSION FAILED')
        except Exception as e:
            print(f'Unexpected error during urllib request: {e}')
            traceback.print_exc()
            print('CONVERSION FAILED')
except Exception as e:
    print(f'Error during conversion: {e}')
    traceback.print_exc()
    print('CONVERSION FAILED')
" 2>&1


# --- Check for various potential output files ---

echo "Checking for output files..."
if [ -f "$API_DIR/output.$OUTPUT_FORMAT" ]; then
    echo "Conversion completed successfully! Output file found."

    # Get content from the converted file
    OUTPUT_SIZE=$(wc -c < "$API_DIR/output.$OUTPUT_FORMAT")
    echo "Output file found with size: $OUTPUT_SIZE bytes"

    # Calculate the access URL for result display
    RESULT_URL="https://api.apify.com/v2/key-value-stores/${APIFY_DEFAULT_KEY_VALUE_STORE_ID}/records/OUTPUT"

    echo "=============================="
    echo "PROCESSING COMPLETE!"
    echo "Document URL: ${DOCUMENT_URL}"
    echo "Output format: ${OUTPUT_FORMAT}"
    echo "Output size: ${OUTPUT_SIZE} bytes"
    echo "=============================="

    # Set the output content type based on format
    CONTENT_TYPE="text/plain"
    case "$OUTPUT_FORMAT" in
        md) CONTENT_TYPE="text/markdown" ;;
        html) CONTENT_TYPE="text/html" ;;
        json) CONTENT_TYPE="application/json" ;;
        text) CONTENT_TYPE="text/plain" ;;
    esac

    # Upload the document content using our function
    upload_to_kvs "$API_DIR/output.$OUTPUT_FORMAT" "OUTPUT" "$CONTENT_TYPE" "Document content"

    # Only proceed with dataset record if document upload succeeded
    if [ $? -eq 0 ]; then
        echo "Your document is available at: ${RESULT_URL}"
        echo "=============================="

        # Find the Apify CLI again (reusing the function's logic would be better, but for clarity we'll repeat)
        APIFY_CMD=""
        for cmd in "apify" "actor" "/usr/local/bin/apify" "/usr/bin/apify" "/opt/apify/cli/bin/apify"; do
            if command -v "$cmd" &> /dev/null; then
                APIFY_CMD="$cmd"
                break
            fi
        done

        if [ -n "$APIFY_CMD" ]; then
            # Add record to dataset with enhanced version check prevention
            echo "Adding record to dataset..."

            # Create a temporary home directory with write permissions
            export TMPDIR="/tmp/apify-home-${RANDOM}"
            mkdir -p "$TMPDIR"

            # Multiple strategies to disable version checking
            export APIFY_DISABLE_VERSION_CHECK=1
            export NODE_OPTIONS="--no-warnings"
            export HOME="$TMPDIR"  # Override home directory to writable location

            # Use the --no-update-notifier flag if available
            if $APIFY_CMD --help | grep -q "\--no-update-notifier"; then
                if $APIFY_CMD --no-update-notifier actor:push-data "{\"url\": \"${DOCUMENT_URL}\", \"output_file\": \"${RESULT_URL}\", \"status\": \"success\"}"; then
                    echo "Successfully added record to dataset"
                else
                    echo "Warning: Failed to add record to dataset"
                fi
            else
                # Fall back to regular command
                if $APIFY_CMD actor:push-data "{\"url\": \"${DOCUMENT_URL}\", \"output_file\": \"${RESULT_URL}\", \"status\": \"success\"}"; then
                    echo "Successfully added record to dataset"
                else
                    echo "Warning: Failed to add record to dataset"
                fi
            fi

            rm -rf "$TMPDIR" 2>/dev/null || true  # Clean up temp dir
        fi
    fi
else
    echo "ERROR: No converted output file found at $API_DIR/output.$OUTPUT_FORMAT"

    # Create error metadata
    ERROR_METADATA="{\"status\":\"error\",\"error\":\"No converted output file found\",\"documentUrl\":\"$DOCUMENT_URL\"}"
    echo "$ERROR_METADATA" > "/tmp/actor-output/OUTPUT"
    chmod 644 "/tmp/actor-output/OUTPUT"

    echo "Error information has been saved to /tmp/actor-output/OUTPUT"
fi


# --- Verify output files for debugging ---

echo "=== Final Output Verification ==="
echo "Files in /tmp/actor-output:"
ls -la /tmp/actor-output/ 2>/dev/null || echo "Cannot list /tmp/actor-output/"

echo "All operations completed. The output should be available in the default key-value store."
echo "Content URL: ${RESULT_URL:-No URL available}"


# --- Cleanup function ---

cleanup() {
    echo "Running cleanup..."

    # Stop the API process
    if [ -n "$API_PID" ]; then
        echo "Stopping docling-serve API (PID: $API_PID)..."
        kill $API_PID 2>/dev/null || true
    fi

    # Export log file to KVS if it exists
    # DO THIS BEFORE REMOVING TOOLS DIRECTORY
    if [ -f "$LOG_FILE" ]; then
        if [ -s "$LOG_FILE" ]; then
            echo "Log file is not empty, pushing to key-value store (key: LOG)..."

            # Upload log using our function
            upload_to_kvs "$LOG_FILE" "LOG" "text/plain" "Log file"
        else
            echo "Warning: log file exists but is empty"
        fi
    else
        echo "Warning: No log file found"
    fi

    # Clean up temporary files AFTER log is uploaded
    echo "Cleaning up temporary files..."
    if [ -d "$API_DIR" ]; then
        echo "Removing API working directory: $API_DIR"
        rm -rf "$API_DIR" 2>/dev/null || echo "Warning: Failed to remove $API_DIR"
    fi

    if [ -d "$TOOLS_DIR" ]; then
        echo "Removing tools directory: $TOOLS_DIR"
        rm -rf "$TOOLS_DIR" 2>/dev/null || echo "Warning: Failed to remove $TOOLS_DIR"
    fi

    # Keep log file until the very end
    echo "Script execution completed at $(date)"
    echo "Actor execution completed"
}

# Register cleanup
trap cleanup EXIT
