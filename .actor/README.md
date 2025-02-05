# Docling Actor on Apify

[![Docling Actor](https://apify.com/actor-badge?actor=vancura/docling?fpr=docling)](https://apify.com/vancura/docling)

This Actor wraps the [Docling project](https://ds4sd.github.io/docling/) to provide serverless document processing in the cloud. It can process complex documents (PDF, DOCX, images) and convert them into structured formats (Markdown, JSON, HTML, Text, or DocTags) with optional OCR support.

## Table of Contents

1. [Features](#features)
2. [Usage](#usage)
3. [Input Parameters](#input-parameters)
4. [Output](#output)
5. [Performance & Resources](#performance--resources)
6. [Troubleshooting](#troubleshooting)
7. [Local Development](#local-development)
8. [Requirements & Installation](#requirements--installation)
9. [License](#license)
10. [Acknowledgments](#acknowledgments)

## Features

- Runs Docling v2.17.0 in a fully managed environment on Apify
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
4. The Actor will run and produce its outputs in the default Key-Value Store under the key `OUTPUT_RESULT`.

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

After processing, the final document is saved as `OUTPUT_RESULT` in the default Key-Value Store.
If the Actor logs warnings or debug info, these messages can be pushed to `DOCLING_LOG`.

You can retrieve the results programmatically by calling:

```bash
apify key-value-stores get-value OUTPUT_RESULT
```

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

## Performance & Resources

- **Docker Image Size**: ~6 GB (includes OCR libraries and ML models)
- **Memory Requirements**:
  - Minimum: 4 GB RAM
  - Recommended: 8 GB RAM for large documents
- **Processing Time**:
  - Simple documents: 30-60 seconds
  - Complex PDFs with OCR: 2-5 minutes
  - Large documents (100+ pages): 5-15 minutes

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

3. **Memory Issues**
   - For large documents, try splitting them into smaller chunks
   - Consider using a higher-memory compute unit
   - Disable OCR if not strictly necessary

4. **Output Format Issues**
   - Verify the output format is supported
   - Check if the document structure is compatible
   - Review the `DOCLING_LOG` for specific errors

## Local Development

If you wish to develop or modify this Actor locally:

1. Clone the repository.
2. Ensure Docker is installed.
3. The Actor files are located in the `.actor` directory:
   - `Dockerfile` - Defines the container environment
   - `actor.json` - Actor configuration and metadata
   - `actor.sh` - Main execution script
   - `input_schema.json` - Input parameter definitions
   - `.dockerignore` - Build optimization rules
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
├── .dockerignore       # Build exclusions
└── README.md           # This documentation
```

## Requirements & Installation

- An [Apify account](https://console.apify.com/?fpr=docling) (free tier available)
- For local development:
  - Docker installed
  - Apify CLI (`npm install -g apify-cli`)
  - Git for version control
- The Actor's Docker image (~6 GB) includes:
  - Python 3.11 with optimized caching (.pyc, .pyo excluded)
  - Node.js 20.x
  - Docling v2.17.0 and its dependencies
  - OCR libraries and ML models

### Build Optimizations

The Actor uses several optimizations to maintain efficiency:

- Python cache files (`pycache`, `.pyc`, `.pyo`, `.pyd`) are excluded
- Development artifacts (`.git`, `.env`, `.venv`) are ignored
- Log and test files (`*.log`, `.pytest_cache`, `.coverage`) are excluded from builds

## License

This wrapper project is under the MIT License, matching the original Docling license. See [LICENSE](../LICENSE) for details.

## Acknowledgments

- [Docling](https://ds4sd.github.io/docling/) codebase by IBM
- [Apify](https://apify.com/?fpr=docling) for the serverless actor environment
