# RAG-onboard

Backend onboarding service for ingesting, processing, and indexing technical documents (manuals, datasheets) with AI-powered extraction and retrieval.

## Project Overview

Built a FastAPI-based onboarding pipeline focused on document lifecycle management: upload, processing, preview generation, secure storage, and RAG indexing for downstream retrieval workflows.

## Scope and Responsibilities (Onboarding Only)

### Document Processing Pipeline
- Implemented end-to-end PDF processing with `PyMuPDF` for page extraction, page count handling, and preview generation.
- Added async-safe execution for CPU-heavy processing using `asyncio.to_thread`.
- Handled malformed/corrupt file scenarios with domain-specific exception handling.

### Storage and File Lifecycle
- Built async S3 integrations (`aioboto3`) for upload, download, delete, and metadata operations.
- Implemented secure separation between private onboarding storage and CDN-served content.
- Added document migration flow (CDN to S3) after processing and indexing.

### RAG Indexing Integration
- Integrated `Ragie` for document ingestion and indexing with environment partition isolation.
- Enriched indexed records with metadata (`asset_id`, category, manufacturer, model, filename) to support filtered retrieval.
- Persisted ingestion identifiers for document lifecycle tracking.

### Onboarding Service Architecture
- Designed onboarding orchestration to coordinate processing, storage migration, preview generation, and indexing.
- Implemented status progression for documents/assets (`PENDING`, `PROCESSING`, `INGESTED`, `FAILED`).
- Added checksum-based integrity and duplicate detection logic.

### Search and AI Integration
- Built document search abstraction over RAG retrieval.
- Integrated Tavily-backed filtering/supplementary search flow where needed.
- Integrated Anthropic client abstractions for AI-assisted analysis and metadata workflows.

### API and Reliability
- Implemented FastAPI endpoints for onboarding and health flows.
- Added structured exception handling and consistent API validation with Pydantic models.
- Maintained structured logging patterns for operational visibility.

### Engineering Practices
- Followed clean architecture with interfaces, repositories, and service-layer separation.
- Used dependency injection (`injector`) for testability and loose coupling.
- Added async-friendly test setup with `pytest` and mocked external dependencies.

## Tech Stack

- **Language/Framework:** Python 3.11+, FastAPI
- **Cloud:** AWS S3, AWS SSM
- **AI/RAG:** Anthropic, Ragie, Tavily
- **Document Processing:** PyMuPDF, Pillow
- **Tooling:** Docker, uv, pytest

## Key Outcomes

- Delivered a production-oriented onboarding pipeline for technical documents.
- Enabled secure document ingestion with searchable indexed content.
- Improved reliability with explicit status tracking, structured errors, and async-safe processing patterns.