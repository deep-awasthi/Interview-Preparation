"""Unit tests for XML serializers and S3 error response formatting."""

import pytest
import xml.etree.ElementTree as ET
from aether.core.exceptions import NoSuchBucketError
from aether.core.utils import parse_range_header
from aether.core.xml import serialize_list_buckets, serialize_initiate_multipart_upload_result


class DummyBucket:
    def __init__(self, name, created_at=None):
        self.name = name
        self.created_at = created_at


def test_no_such_bucket_error_xml():
    err = NoSuchBucketError("The specified bucket does not exist.", resource="/testbucket")
    xml_str = err.to_xml()

    assert "<Code>NoSuchBucket</Code>" in xml_str
    assert "<Resource>/testbucket</Resource>" in xml_str
    assert "<Message>" in xml_str


def test_serialize_list_buckets():
    buckets = [DummyBucket("bucket1"), DummyBucket("bucket2")]
    xml_bytes = serialize_list_buckets(buckets)
    xml_str = xml_bytes.decode("utf-8")

    assert "<ListAllMyBucketsResult" in xml_str
    assert "<Name>bucket1</Name>" in xml_str
    assert "<Name>bucket2</Name>" in xml_str


def test_serialize_initiate_multipart_upload():
    xml_bytes = serialize_initiate_multipart_upload_result("mybucket", "file.mp4", "upload-123")
    xml_str = xml_bytes.decode("utf-8")

    assert "<Bucket>mybucket</Bucket>" in xml_str
    assert "<Key>file.mp4</Key>" in xml_str
    assert "<UploadId>upload-123</UploadId>" in xml_str


def test_parse_range_header():
    start, end = parse_range_header("bytes=0-499", 1000)
    assert start == 0
    assert end == 499

    start, end = parse_range_header("bytes=500-", 1000)
    assert start == 500
    assert end == 999
