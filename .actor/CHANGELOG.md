# Changelog

All notable changes to the Docling Actor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-03-15

### Changed

- Switched from full Docling CLI to docling-serve API
- Dramatically reduced Docker image size (from ~6GB to ~600MB)
- Improved API compatibility with docling-serve
- Better content type handling for different output formats
- Updated error handling to align with API responses

### Technical Details

- Actor Specification v1
- Using ds4sd/docling-serve:latest base image
- Node.js 20.x for Apify CLI
- Eliminated Python dependencies
- Simplified Docker build process

## [1.0.0] - 2025-02-07

### Added

- Initial release of Docling Actor
- Support for multiple document formats (PDF, DOCX, images)
- OCR capabilities for scanned documents
- Multiple output formats (md, json, html, text, doctags)
- Comprehensive error handling and logging
- Dataset records with processing status
- Memory monitoring and resource optimization
- Security features including non-root user execution

### Technical Details

- Actor Specification v1
- Docling v2.17.0
- Python 3.11
- Node.js 20.x
- Comprehensive error codes:
  - 10: Invalid input
  - 11: URL inaccessible
  - 12: Docling processing failed
  - 13: Output file missing
  - 14: Storage operation failed
  - 15: OCR processing failed
