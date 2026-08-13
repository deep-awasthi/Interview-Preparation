# Aether: Open-Source S3-Compatible Object Storage

Aether is an S3-compatible Object Storage Server built entirely in Python using Django 5.x, PostgreSQL, Redis, Celery, and Nginx.

## Key Features

- **Full S3 SDK Compatibility**: Unmodified AWS SDKs (`boto3`, Java AWS SDK, Go AWS SDK, AWS CLI) work out-of-the-box by setting `endpoint_url`.
- **AWS Signature Version 4 (SigV4)**: Full native HMAC-SHA256 authentication header and presigned URL verification.
- **Clean Layered Architecture**: Strictly decouples HTTP views from domain services and storage drivers.
- **Storage Engine Abstraction**: `FilesystemDriver` streams binary objects to disk with modular driver stubs for future cloud backends.
- **Advanced S3 Capabilities**:
  - Multipart Uploads (Initiate, Upload Part, List Parts, Complete, Abort)
  - Streaming Uploads & Chunked Download Responses
  - Range Requests (`Range: bytes=start-end`)
  - Object Versioning & Delete Markers
  - Bucket Policies & Access Control
  - Object Locking (Governance & Compliance)
  - Asynchronous Background Cleanup via Celery Beat
