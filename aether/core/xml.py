"""S3 XML Serializers matching AWS S3 API XML structure."""

import xml.etree.ElementTree as ET
from typing import Any, List, Optional
from aether.core.utils import format_iso8601

S3_XMLNS = "http://s3.amazonaws.com/doc/2006-03-01/"


def _to_xml_bytes(root: ET.Element) -> bytes:
    """Helper to convert ElementTree to utf-8 XML bytes with declaration."""
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def serialize_list_buckets(buckets: List[Any], owner_id: str = "aether-owner-id", owner_name: str = "aether-admin") -> bytes:
    """Serialize GET / response (ListAllMyBucketsResult)."""
    root = ET.Element("ListAllMyBucketsResult", xmlns=S3_XMLNS)

    owner = ET.SubElement(root, "Owner")
    ET.SubElement(owner, "ID").text = owner_id
    ET.SubElement(owner, "DisplayName").text = owner_name

    buckets_elem = ET.SubElement(root, "Buckets")
    for b in buckets:
        bucket_elem = ET.SubElement(buckets_elem, "Bucket")
        ET.SubElement(bucket_elem, "Name").text = b.name
        ET.SubElement(bucket_elem, "CreationDate").text = format_iso8601(b.created_at)

    return _to_xml_bytes(root)


def serialize_list_objects_v2(
    bucket_name: str,
    objects: List[Any],
    common_prefixes: List[str],
    is_truncated: bool = False,
    max_keys: int = 1000,
    prefix: str = "",
    delimiter: str = "",
    continuation_token: Optional[str] = None,
    next_continuation_token: Optional[str] = None,
    key_count: int = 0,
    owner_id: str = "aether-owner-id",
    owner_name: str = "aether-admin",
) -> bytes:
    """Serialize GET /<bucket>?list-type=2 response (ListBucketResult V2)."""
    root = ET.Element("ListBucketResult", xmlns=S3_XMLNS)

    ET.SubElement(root, "Name").text = bucket_name
    ET.SubElement(root, "Prefix").text = prefix
    if delimiter:
        ET.SubElement(root, "Delimiter").text = delimiter
    ET.SubElement(root, "MaxKeys").text = str(max_keys)
    ET.SubElement(root, "KeyCount").text = str(key_count)
    ET.SubElement(root, "IsTruncated").text = "true" if is_truncated else "false"

    if continuation_token:
        ET.SubElement(root, "ContinuationToken").text = continuation_token
    if next_continuation_token:
        ET.SubElement(root, "NextContinuationToken").text = next_continuation_token

    for obj in objects:
        contents = ET.SubElement(root, "Contents")
        ET.SubElement(contents, "Key").text = obj.key
        ET.SubElement(contents, "LastModified").text = format_iso8601(obj.last_modified)
        ET.SubElement(contents, "ETag").text = f'"{obj.etag}"' if not obj.etag.startswith('"') else obj.etag
        ET.SubElement(contents, "Size").text = str(obj.size)
        ET.SubElement(contents, "StorageClass").text = obj.storage_class or "STANDARD"

        owner = ET.SubElement(contents, "Owner")
        ET.SubElement(owner, "ID").text = owner_id
        ET.SubElement(owner, "DisplayName").text = owner_name

    for cp in common_prefixes:
        cp_elem = ET.SubElement(root, "CommonPrefixes")
        ET.SubElement(cp_elem, "Prefix").text = cp

    return _to_xml_bytes(root)


def serialize_list_objects_v1(
    bucket_name: str,
    objects: List[Any],
    common_prefixes: List[str],
    is_truncated: bool = False,
    max_keys: int = 1000,
    prefix: str = "",
    delimiter: str = "",
    marker: str = "",
    next_marker: str = "",
    owner_id: str = "aether-owner-id",
    owner_name: str = "aether-admin",
) -> bytes:
    """Serialize GET /<bucket> response (ListBucketResult V1)."""
    root = ET.Element("ListBucketResult", xmlns=S3_XMLNS)

    ET.SubElement(root, "Name").text = bucket_name
    ET.SubElement(root, "Prefix").text = prefix
    ET.SubElement(root, "Marker").text = marker
    if next_marker:
        ET.SubElement(root, "NextMarker").text = next_marker
    if delimiter:
        ET.SubElement(root, "Delimiter").text = delimiter
    ET.SubElement(root, "MaxKeys").text = str(max_keys)
    ET.SubElement(root, "IsTruncated").text = "true" if is_truncated else "false"

    for obj in objects:
        contents = ET.SubElement(root, "Contents")
        ET.SubElement(contents, "Key").text = obj.key
        ET.SubElement(contents, "LastModified").text = format_iso8601(obj.last_modified)
        ET.SubElement(contents, "ETag").text = f'"{obj.etag}"' if not obj.etag.startswith('"') else obj.etag
        ET.SubElement(contents, "Size").text = str(obj.size)
        ET.SubElement(contents, "StorageClass").text = obj.storage_class or "STANDARD"

        owner = ET.SubElement(contents, "Owner")
        ET.SubElement(owner, "ID").text = owner_id
        ET.SubElement(owner, "DisplayName").text = owner_name

    for cp in common_prefixes:
        cp_elem = ET.SubElement(root, "CommonPrefixes")
        ET.SubElement(cp_elem, "Prefix").text = cp

    return _to_xml_bytes(root)


def serialize_copy_object_result(etag: str, last_modified: Any) -> bytes:
    """Serialize PUT /<bucket>/<key> with copy source response (CopyObjectResult)."""
    root = ET.Element("CopyObjectResult", xmlns=S3_XMLNS)
    formatted_etag = f'"{etag}"' if not etag.startswith('"') else etag
    ET.SubElement(root, "ETag").text = formatted_etag
    ET.SubElement(root, "LastModified").text = format_iso8601(last_modified)
    return _to_xml_bytes(root)


def serialize_initiate_multipart_upload_result(bucket: str, key: str, upload_id: str) -> bytes:
    """Serialize POST /<bucket>/<key>?uploads response (InitiateMultipartUploadResult)."""
    root = ET.Element("InitiateMultipartUploadResult", xmlns=S3_XMLNS)
    ET.SubElement(root, "Bucket").text = bucket
    ET.SubElement(root, "Key").text = key
    ET.SubElement(root, "UploadId").text = upload_id
    return _to_xml_bytes(root)


def serialize_list_parts_result(
    bucket: str,
    key: str,
    upload_id: str,
    parts: List[Any],
    max_parts: int = 1000,
    part_number_marker: int = 0,
    is_truncated: bool = False,
    next_part_number_marker: int = 0,
) -> bytes:
    """Serialize GET /<bucket>/<key>?uploadId=... response (ListPartsResult)."""
    root = ET.Element("ListPartsResult", xmlns=S3_XMLNS)
    ET.SubElement(root, "Bucket").text = bucket
    ET.SubElement(root, "Key").text = key
    ET.SubElement(root, "UploadId").text = upload_id
    ET.SubElement(root, "PartNumberMarker").text = str(part_number_marker)
    ET.SubElement(root, "NextPartNumberMarker").text = str(next_part_number_marker)
    ET.SubElement(root, "MaxParts").text = str(max_parts)
    ET.SubElement(root, "IsTruncated").text = "true" if is_truncated else "false"

    for p in parts:
        part_elem = ET.SubElement(root, "Part")
        ET.SubElement(part_elem, "PartNumber").text = str(p.part_number)
        ET.SubElement(part_elem, "LastModified").text = format_iso8601(p.last_modified)
        ET.SubElement(part_elem, "ETag").text = f'"{p.etag}"' if not p.etag.startswith('"') else p.etag
        ET.SubElement(part_elem, "Size").text = str(p.size)

    return _to_xml_bytes(root)


def serialize_complete_multipart_upload_result(bucket: str, key: str, etag: str, location: str = "") -> bytes:
    """Serialize POST /<bucket>/<key>?uploadId=... response (CompleteMultipartUploadResult)."""
    root = ET.Element("CompleteMultipartUploadResult", xmlns=S3_XMLNS)
    ET.SubElement(root, "Location").text = location or f"http://localhost:8000/{bucket}/{key}"
    ET.SubElement(root, "Bucket").text = bucket
    ET.SubElement(root, "Key").text = key
    formatted_etag = f'"{etag}"' if not etag.startswith('"') else etag
    ET.SubElement(root, "ETag").text = formatted_etag
    return _to_xml_bytes(root)
