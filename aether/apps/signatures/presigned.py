"""Presigned URL Generator for Aether."""

import hmac
import hashlib
import urllib.parse
from datetime import datetime, timezone
from aether.apps.signatures.validator import get_signature_key


def generate_presigned_url(
    method: str,
    bucket: str,
    key: str,
    access_key_id: str,
    secret_access_key: str,
    expires_in: int = 3600,
    region: str = "us-east-1",
    host: str = "http://localhost:8000",
) -> str:
    """Generate AWS SigV4 compliant presigned URL for GET or PUT request.

    Args:
        method: 'GET' or 'PUT'
        bucket: Bucket name
        key: Object key
        access_key_id: Access key
        secret_access_key: Secret key
        expires_in: Expiration time in seconds
        region: AWS region string
        host: Server base URL

    Returns:
        Full presigned URL string.
    """
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    path = f"/{bucket}/{key.lstrip('/')}"
    service = "s3"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    credential = f"{access_key_id}/{credential_scope}"

    query_params = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": credential,
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires_in),
        "X-Amz-SignedHeaders": "host",
    }

    # Canonical Query String
    sorted_params = []
    for k in sorted(query_params.keys()):
        sorted_params.append(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(query_params[k], safe='')}"
        )
    canonical_query_string = "&".join(sorted_params)

    # Parse host authority for Canonical Headers
    parsed_host = urllib.parse.urlparse(host)
    host_header = parsed_host.netloc or host.replace("http://", "").replace("https://", "")

    canonical_headers = f"host:{host_header.lower()}\n"
    signed_headers = "host"
    payload_hash = "UNSIGNED-PAYLOAD"

    canonical_uri = urllib.parse.quote(path, safe="/")
    canonical_request = "\n".join([
        method.upper(),
        canonical_uri,
        canonical_query_string,
        canonical_headers,
        signed_headers,
        payload_hash,
    ])

    hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256",
        amz_date,
        credential_scope,
        hashed_canonical_request,
    ])

    signing_key = get_signature_key(secret_access_key, date_stamp, region, service)
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    full_url = f"{host.rstrip('/')}{path}?{canonical_query_string}&X-Amz-Signature={signature}"
    return full_url
