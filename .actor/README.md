# Docling Actor on Apify

[![Docling Actor](https://apify.com/actor-badge?actor=vancura/docling?fpr=docling)](https://apify.com/vancura/docling)

This Actor (specification v1) wraps the [Docling project](https://ds4sd.github.io/docling/) to provide serverless document processing in the cloud. It can process complex documents (PDF, DOCX, images) and convert them into structured formats (Markdown, JSON, HTML, Text, or DocTags) with optional OCR support.

## What are Actors?

[Actors](https://docs.apify.com/platform/actors?fpr=docling) are serverless microservices running on the [Apify Platform](https://apify.com/?fpr=docling). They are based on the [Actor SDK](https://docs.apify.com/sdk/js?fpr=docling) and can be found in the [Apify Store](https://apify.com/store?fpr=docling). Learn more about Actors in the [Apify Whitepaper](https://whitepaper.actor?fpr=docling).

## Table of Contents

1. [Features](#features)
2. [Usage](#usage)
3. [Input Parameters](#input-parameters)
4. [Output](#output)
5. [Performance & Resources](#performance--resources)
6. [Troubleshooting](#troubleshooting)
7. [Local Development](#local-development)
8. [Architecture](#architecture)
9. [License](#license)
10. [Acknowledgments](#acknowledgments)
11. [Security Considerations](#security-considerations)

## Features

- Leverages the lightweight docling-serve API for efficient document processing
- Processes multiple document formats:
  - PDF documents (scanned or digital)
  - Microsoft Office files (DOCX, XLSX, PPTX)
  - Images (PNG, JPG, TIFF)
  - Other text-based formats
- Provides OCR capabilities for scanned documents
- Exports to multiple formats:
  - Markdown
  - JSON
  - HTML
  - Plain Text
  - DocTags (structured format)
- No local setup needed—just provide input via a simple JSON config

## Usage

### Using Apify Console

1. Go to the Apify Actor page.
2. Click "Run".
3. In the input form, fill in:
   - The URL of the document.
   - Output format (`md`, `json`, `html`, `text`, or `doctags`).
   - OCR boolean toggle.
4. The Actor will run and produce its outputs in the default key-value store under the key `OUTPUT_RESULT`.

### Using Apify API

```bash
curl --request POST \
  --url "https://api.apify.com/v2/acts/username~actorname/run" \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_API_TOKEN' \
  --data '{
    "documentUrl": "https://arxiv.org/pdf/2408.09869.pdf",
    "outputFormat": "md",
    "ocr": true
  }'
```

### Using Apify CLI

```bash
apify call username/actorname --input='{
    "documentUrl": "https://arxiv.org/pdf/2408.09869.pdf",
    "outputFormat": "md",
    "ocr": true
}'
```

## Input Parameters

The Actor accepts a JSON schema matching the file `.actor/input_schema.json`. Below is a summary of the fields:

| Field          | Type    | Required | Default  | Description                                                                                               |
|----------------|---------|----------|----------|-----------------------------------------------------------------------------------------------------------|
| `documentUrl`  | string  | Yes      | None     | URL of the document (PDF, image, DOCX, etc.) to be processed. Must be directly accessible via public URL. |
| `outputFormat` | string  | No       | `md`     | Desired output format. One of `md`, `json`, `html`, `text`, or `doctags`.                                 |
| `ocr`          | boolean | No       | `true`   | If set to true, OCR will be applied to scanned PDFs or images for text recognition.                       |

### Example Input

```json
{
    "documentUrl": "https://arxiv.org/pdf/2408.09869.pdf",
    "outputFormat": "md",
    "ocr": false
}
```

## Output

The Actor provides three types of outputs:

1. **Processed Document** - The Actor will provide the direct URL to your result in the run log, looking like:

   ```text
   You can find your results at: 'https://api.apify.com/v2/key-value-stores/[YOUR_STORE_ID]/records/OUTPUT_RESULT'
   ```

2. **Processing Log** - Available in the key-value store as `DOCLING_LOG`

3. **Dataset Record** - Contains processing metadata with:
   - Input document URL
   - Direct link to the processed output
   - Processing status

You can access the results in several ways:

1. **Direct URL** (shown in Actor run logs):

```text
https://api.apify.com/v2/key-value-stores/[STORE_ID]/records/OUTPUT_RESULT
```

2. **Programmatically** via Apify CLI:

```bash
apify key-value-stores get-value OUTPUT_RESULT
```

3. **Dataset** - Check the "Dataset" tab in the Actor run details to see processing metadata

### Example Outputs

#### Markdown (md)

```markdown
# Document Title

## Section 1
Content of section 1...

## Section 2
Content of section 2...
```

#### JSON

```json
{
    "title": "Document Title",
    "sections": [
        {
            "level": 1,
            "title": "Section 1",
            "content": "Content of section 1..."
        }
    ]
}
```

#### HTML

```html
<h1>Document Title</h1>
<h2>Section 1</h2>
<p>Content of section 1...</p>
```

### Processing Logs (`DOCLING_LOG`)

The Actor maintains detailed processing logs including:

- API request and response details
- Processing steps and timing
- Error messages and stack traces
- Input validation results

Access logs via:

```bash
apify key-value-stores get-record DOCLING_LOG
```

## Performance & Resources

- **Docker Image Size**: ~600 MB
- **Memory Requirements**:
  - Minimum: 2 GB RAM
  - Recommended: 4 GB RAM for large or complex documents
- **Processing Time**:
  - Simple documents: 15-30 seconds
  - Complex PDFs with OCR: 1-3 minutes
  - Large documents (100+ pages): 3-10 minutes

## Troubleshooting

Common issues and solutions:

1. **Document URL Not Accessible**
   - Ensure the URL is publicly accessible
   - Check if the document requires authentication
   - Verify the URL leads directly to the document

2. **OCR Processing Fails**
   - Verify the document is not password-protected
   - Check if the image quality is sufficient
   - Try processing with OCR disabled

3. **API Response Issues**
   - Check the logs for detailed error messages
   - Ensure the document format is supported
   - Verify the URL is correctly formatted

4. **Output Format Issues**
   - Verify the output format is supported
   - Check if the document structure is compatible
   - Review the `DOCLING_LOG` for specific errors

### Error Handling

The Actor implements comprehensive error handling:

- Input validation for document URLs and parameters
- Detailed error messages in `DOCLING_LOG`
- Proper exit codes for different failure scenarios
- Automatic cleanup on failure
- Dataset records with processing status

## Local Development

If you wish to develop or modify this Actor locally:

1. Clone the repository.
2. Ensure Docker is installed.
3. The Actor files are located in the `.actor` directory:
   - `Dockerfile` - Defines the container environment
   - `actor.json` - Actor configuration and metadata
   - `actor.sh` - Main execution script
   - `input_schema.json` - Input parameter definitions
4. Run the Actor locally using:

   ```bash
   apify run
   ```

### Actor Structure

```text
.actor/
├── Dockerfile          # Container definition
├── actor.json          # Actor metadata
├── actor.sh            # Execution script
├── input_schema.json   # Input parameters
└── README.md           # This documentation
```

## Architecture

This Actor uses a lightweight architecture based on the official `ds4sd/docling-serve` Docker image:

- **Base Image**: `ds4sd/docling-serve:latest` (~600MB)
- **API Communication**: Uses the RESTful API provided by docling-serve on port 8080
- **Request Flow**:
  1. Actor receives the input parameters
  2. Creates a JSON payload for the docling-serve API
  3. Makes a POST request to the /convert endpoint
  4. Processes the response and stores it in the key-value store
- **Dependencies**: 
  - Node.js for Apify CLI
  - Essential Linux tools (curl, jq, etc.)
- **Security**: Runs as a non-root user for enhanced security

## License

This wrapper project is under the MIT License, matching the original Docling license. See [LICENSE](../LICENSE) for details.

## Acknowledgments

- [Docling](https://ds4sd.github.io/docling/) and [docling-serve](https://github.com/DS4SD/docling-serve) by IBM
- [Apify](https://apify.com/?fpr=docling) for the serverless actor environment

## Security Considerations

- Actor runs under a non-root user for enhanced security
- Input URLs are validated before processing
- Temporary files are securely managed and cleaned up
- Process isolation through Docker containerization
- Secure handling of processing artifacts
