#!/usr/bin/env python3
"""
Document Processing Script for Docling-Serve API

This script handles the communication with the docling-serve API,
processes the conversion request, and saves the output to the specified location.
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Global constants
DEFAULT_TIMEOUT = 300  # 5 minutes
OUTPUT_FORMATS = ["md", "html", "json", "text"]


def setup_arg_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="Process documents using docling-serve API")
    parser.add_argument("--api-endpoint", required=True, help="Docling API endpoint URL")
    parser.add_argument("--request-json", required=True, help="Path to JSON file with request data")
    parser.add_argument("--output-dir", required=True, help="Directory to save output files")
    parser.add_argument("--output-format", required=True, help="Desired output format")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout in seconds")
    return parser


def load_request_data(json_path: str) -> Dict:
    """Load request data from JSON file."""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading request data: {e}")
        sys.exit(1)


def save_response_diagnostics(response_text: str, status_code: int, headers: Dict, output_dir: str) -> None:
    """Save full response and headers for debugging."""
    with open(os.path.join(output_dir, "full_response.txt"), 'w') as f:
        f.write(f"Status code: {status_code}\n")
        f.write(f"Headers: {headers}\n\n")

        # Truncate very long responses
        if len(response_text) > 10000:
            f.write(f"Content: {response_text[:10000]}...")
        else:
            f.write(f"Content: {response_text}")


def save_response_json(response_text: str, output_dir: str) -> None:
    """Save raw response JSON."""
    with open(os.path.join(output_dir, "response.json"), 'w') as f:
        f.write(response_text)


def save_structure_info(data: Dict, output_dir: str) -> None:
    """Save detailed information about response structure."""
    with open(os.path.join(output_dir, "response_structure.txt"), 'w') as f:
        f.write(f'Response keys: {list(data.keys())}\n')

        # Document content details
        if 'document' in data:
            doc = data['document'] or {}
            f.write(f'Document keys: {list(doc.keys() if doc else [])}\n')

            # Check specific content fields
            for content_type in ['html_content', 'md_content', 'text_content', 'json_content']:
                if content_type in doc and doc[content_type]:
                    f.write(f'{content_type.replace("_content", "").upper()} content length: {len(doc[content_type])}\n')
                elif content_type in doc:
                    f.write(f'{content_type.replace("_content", "").upper()} content is present but empty or null\n')

        # Output structure details
        if 'outputs' in data:
            f.write(f'Outputs count: {len(data["outputs"])}\n')
            if data['outputs']:
                output = data['outputs'][0]
                f.write(f'First output keys: {list(output.keys())}\n')

                if 'files' in output:
                    f.write(f'Files count: {len(output["files"])}\n')
                    if output['files']:
                        file_data = output['files'][0]
                        f.write(f'First file keys: {list(file_data.keys())}\n')
                        if 'content' in file_data:
                            content_length = len(file_data['content'])
                            f.write(f'Content length: {content_length}\n')


def extract_content_from_file_output(data: Dict, output_format: str, output_dir: str) -> bool:
    """Extract content from 'files' output format."""
    if 'outputs' not in data or not data['outputs']:
        print('No outputs found in response')
        return False

    output = data['outputs'][0]
    if 'files' not in output or not output['files']:
        print('No files found in output')
        print(f'Available fields: {list(output.keys())}')
        return False

    file_data = output['files'][0]
    if 'content' not in file_data or not file_data['content']:
        if 'content' in file_data:
            print('Content field exists but is empty')
        else:
            print('No content field in file data')
            print(f'Available fields: {list(file_data.keys())}')
        return False

    # Content found, save it
    content = file_data['content']
    print(f'Found content in file (length: {len(content)})')
    with open(os.path.join(output_dir, f"output.{output_format}"), 'w') as f:
        f.write(content)
    print('CONVERSION SUCCESS')
    return True


def extract_content_from_document(data: Dict, output_format: str, output_dir: str) -> bool:
    """Extract content from 'document' response format."""
    if 'document' not in data or data.get('status') != 'success':
        print('No document field or success status found in response')
        return False

    document = data['document'] or {}

    # Check available formats
    available_formats = []
    for fmt in ['html', 'md', 'text', 'json']:
        content_field = f'{fmt}_content'
        if content_field in document and document[content_field]:
            available_formats.append((fmt, document[content_field]))

    if not available_formats:
        # Check for empty fields
        empty_fields = []
        for fmt in ['html', 'md', 'text', 'json']:
            content_field = f'{fmt}_content'
            if content_field in document and not document[content_field]:
                empty_fields.append(content_field)

        if empty_fields:
            print(f'Found content fields but they are empty or null: {empty_fields}')
        else:
            print('No content fields found in document')

        print(f'Available fields in document: {list(document.keys() if document else [])}')
        return False

    # Found available formats
    print(f'Found {len(available_formats)} available formats: {[f[0] for f in available_formats]}')

    # First try to find exact requested format
    requested_format_match = next((f for f in available_formats if f[0] == output_format.lower()), None)

    if requested_format_match:
        format_type, content = requested_format_match
        print(f'Found content in requested format {format_type} (length: {len(content)})')
    else:
        # If requested format not found, use the first available
        format_type, content = available_formats[0]
        print(f'Requested format not found, using alternative format {format_type} (length: {len(content)})')

    # Save with the matched format's extension
    with open(os.path.join(output_dir, f"output.{format_type}"), 'w') as f:
        f.write(content)

    # If we're using a different format than requested, also save with requested extension
    if format_type != output_format.lower():
        print(f'Saving content with requested extension {format_type} -> {output_format}')
        with open(os.path.join(output_dir, f"output.{output_format}"), 'w') as f:
            f.write(content)

    print('CONVERSION SUCCESS')
    return True


def process_success_response(response_text: str, output_format: str, output_dir: str) -> bool:
    """Process a successful response and extract document content."""
    try:
        # Save raw response
        save_response_json(response_text, output_dir)

        # Parse JSON
        data = json.loads(response_text)
        print('Successfully parsed response as JSON')

        # Save detailed structure info
        save_structure_info(data, output_dir)

        # Try both response formats
        if extract_content_from_file_output(data, output_format, output_dir):
            return True

        if extract_content_from_document(data, output_format, output_dir):
            return True

        # Check for metadata
        if 'metadata' in data:
            print('Metadata found in response, saving to file')
            with open(os.path.join(output_dir, "metadata.json"), 'w') as f:
                json.dump(data['metadata'], f, indent=2)

        print('CONVERSION PARTIAL - Some data available but not complete')
        return False

    except Exception as json_error:
        print(f'Failed to parse response as JSON: {json_error}')
        traceback.print_exc()

        # Save raw content as text if JSON parsing fails
        with open(os.path.join(output_dir, "output.txt"), 'w') as f:
            f.write(response_text)
        print('Saved raw response as text file')
        print('CONVERSION PARTIAL - Raw response saved')
        return False


def process_requests_api(api_endpoint: str, request_data: Dict, output_format: str, output_dir: str, timeout: int) -> bool:
    """Process using requests library."""
    try:
        import requests
        print('Using requests library for API call')

        # Record start time for timing
        start_time = time.time()
        print(f'Starting conversion request at {time.strftime("%H:%M:%S")}')

        response = requests.post(
            api_endpoint,
            json=request_data,
            timeout=timeout
        )

        elapsed = time.time() - start_time
        print(f'Conversion request completed in {elapsed:.2f} seconds')
        print(f'Response status code: {response.status_code}')

        # Save response diagnostics
        save_response_diagnostics(response.text, response.status_code, dict(response.headers), output_dir)

        if response.status_code == 200:
            return process_success_response(response.text, output_format, output_dir)
        else:
            print(f'Error response: {response.text[:500]}')
            print('CONVERSION FAILED')
            return False

    except Exception as e:
        print(f'Error during requests API call: {e}')
        traceback.print_exc()
        print('CONVERSION FAILED')
        return False


def process_urllib_api(api_endpoint: str, request_data: Dict, output_format: str, output_dir: str, timeout: int) -> bool:
    """Process using urllib as fallback."""
    try:
        import urllib.request
        import urllib.error

        print('Using urllib library for API call')
        headers = {'Content-Type': 'application/json'}
        req_data = json.dumps(request_data).encode('utf-8')

        req = urllib.request.Request(
            api_endpoint,
            data=req_data,
            headers=headers,
            method='POST'
        )

        try:
            start_time = time.time()
            print(f'Starting conversion request at {time.strftime("%H:%M:%S")}')

            with urllib.request.urlopen(req, timeout=timeout) as response:
                elapsed = time.time() - start_time
                print(f'Conversion request completed in {elapsed:.2f} seconds')
                print(f'Response status: {response.status}')

                response_text = response.read().decode('utf-8')
                save_response_diagnostics(response_text, response.status, dict(response.headers), output_dir)

                if response.status == 200:
                    return process_success_response(response_text, output_format, output_dir)
                else:
                    print(f'Error status: {response.status}')
                    print('CONVERSION FAILED')
                    return False

        except urllib.error.HTTPError as e:
            print(f'HTTP Error: {e.code} - {e.reason}')
            print(f'Response body: {e.read().decode("utf-8")[:500]}')
            print('CONVERSION FAILED')
            return False

        except urllib.error.URLError as e:
            print(f'URL Error: {e.reason}')
            print('CONVERSION FAILED')
            return False

        except Exception as e:
            print(f'Unexpected error during urllib request: {e}')
            traceback.print_exc()
            print('CONVERSION FAILED')
            return False

    except Exception as e:
        print(f'Error setting up urllib: {e}')
        traceback.print_exc()
        print('CONVERSION FAILED')
        return False


def process_document(api_endpoint: str, request_json_path: str, output_format: str,
                    output_dir: str, timeout: int) -> bool:
    """Main function to process a document through the docling-serve API."""
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Load request data
        request_data = load_request_data(request_json_path)

        # Log request info
        if 'http_sources' in request_data and request_data['http_sources']:
            print(f'Request to convert URL: {request_data["http_sources"][0]["url"]}')

        if 'options' in request_data:
            options = request_data['options']
            if 'to_formats' in options and options['to_formats']:
                print(f'Output format: {options["to_formats"][0]}')
            if 'ocr' in options:
                print(f'OCR enabled: {options["ocr"]}')

        # Try requests first, fall back to urllib
        try:
            return process_requests_api(api_endpoint, request_data, output_format, output_dir, timeout)
        except ImportError:
            return process_urllib_api(api_endpoint, request_data, output_format, output_dir, timeout)

    except Exception as e:
        print(f'Error during conversion: {e}')
        traceback.print_exc()
        print('CONVERSION FAILED')
        return False


def main():
    """Main entry point."""
    parser = setup_arg_parser()
    args = parser.parse_args()

    success = process_document(
        api_endpoint=args.api_endpoint,
        request_json_path=args.request_json,
        output_format=args.output_format,
        output_dir=args.output_dir,
        timeout=args.timeout
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()