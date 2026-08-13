"""Unit tests for AWS SigV4 Validator and Presigned URL generation."""

import pytest
from aether.apps.signatures.validator import SigV4Validator, get_signature_key
from aether.apps.signatures.presigned import generate_presigned_url


def test_get_signature_key():
    key = get_signature_key("secret", "20260811", "us-east-1", "s3")
    assert isinstance(key, bytes)
    assert len(key) == 32


def test_parse_auth_header():
    header = (
        "AWS4-HMAC-SHA256 "
        "Credential=AKIAIOSFODNN7EXAMPLE/20260811/us-east-1/s3/aws4_request, "
        "SignedHeaders=host;x-amz-date, "
        "Signature=fe5f80f77d5fa3bea10a526707812a0e"
    )
    parsed = SigV4Validator.parse_auth_header(header)
    assert parsed["Credential"].startswith("AKIAIOSFODNN7EXAMPLE")
    assert parsed["SignedHeaders"] == "host;x-amz-date"
    assert parsed["Signature"] == "fe5f80f77d5fa3bea10a526707812a0e"


def test_generate_presigned_url():
    url = generate_presigned_url(
        method="GET",
        bucket="mybucket",
        key="myobject.png",
        access_key_id="admin",
        secret_access_key="password",
        expires_in=3600,
    )
    assert "http://localhost:8000/mybucket/myobject.png" in url
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in url
    assert "X-Amz-Credential=" in url
    assert "X-Amz-Signature=" in url
