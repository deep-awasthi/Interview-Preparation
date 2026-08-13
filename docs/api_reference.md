# S3 API Reference & Compatibility Matrix

| HTTP Method | Resource / Query | S3 Action Name | Supported Status |
|---|---|---|---|
| `GET` | `/` | ListBuckets | Supported |
| `PUT` | `/<bucket>` | CreateBucket | Supported |
| `DELETE` | `/<bucket>` | DeleteBucket | Supported |
| `HEAD` | `/<bucket>` | HeadBucket | Supported |
| `GET` | `/<bucket>?list-type=2` | ListObjectsV2 | Supported |
| `PUT` | `/<bucket>/<key>` | PutObject | Supported |
| `GET` | `/<bucket>/<key>` | GetObject | Supported |
| `HEAD` | `/<bucket>/<key>` | HeadObject | Supported |
| `DELETE` | `/<bucket>/<key>` | DeleteObject | Supported |
| `PUT` | `/<bucket>/<key>` + Header | CopyObject | Supported |
| `POST` | `/<bucket>/<key>?uploads` | CreateMultipartUpload | Supported |
| `PUT` | `/<bucket>/<key>?uploadId=...` | UploadPart | Supported |
| `GET` | `/<bucket>/<key>?uploadId=...` | ListParts | Supported |
| `POST` | `/<bucket>/<key>?uploadId=...` | CompleteMultipartUpload | Supported |
| `DELETE` | `/<bucket>/<key>?uploadId=...` | AbortMultipartUpload | Supported |
