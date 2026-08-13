"""AWS Signature Version 4 (SigV4) verification engine for Aether."""

import hmac
import hashlib
import urllib.parse
from datetime import datetime
from typing import Dict, Optional, Tuple

from aether.core.exceptions import AccessDeniedError, SignatureDoesNotMatchError


def sign(key: bytes, msg: str) -> bytes:
    """HMAC-SHA256 signature helper."""
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    """Derive AWS SigV4 signing key."""
    k_date = sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    k_signing = sign(k_service, "aws4_request")
    return k_signing


class SigV4Validator:
    """Validator for AWS Signature Version 4 requests."""

    @staticmethod
    def parse_auth_header(auth_header: str) -> Dict[str, str]:
        """Parse AWS4-HMAC-SHA256 Authorization header."""
        if not auth_header.startswith("AWS4-HMAC-SHA256"):
            raise SignatureDoesNotMatchError("Unsupported authorization algorithm.")

        params = {}
        parts = auth_header[len("AWS4-HMAC-SHA256 ") :].split(",")
        for part in parts:
            if "=" in part:
                key, val = part.strip().split("=", 1)
                params[key] = val
        return params

    @classmethod
    def verify_request(
        self,
        request,
        secret_key: str,
        payload_hash: Optional[str] = None,
    ) -> bool:
        """Verify SigV4 signature from Authorization header or Presigned query parameters.

        Args:
            request: Django HttpRequest object.
            secret_key: Plaintext secret key associated with the access key.
            payload_hash: Optional override for body hash ('UNSIGNED-PAYLOAD' or SHA256 hex).

        Returns:
            True if signature matches. Raises SignatureDoesNotMatchError otherwise.
        """
        auth_header = request.headers.get("Authorization") or request.META.get("HTTP_AUTHORIZATION")
        if auth_header:
            return self._verify_header_auth(request, auth_header, secret_key, payload_hash)
        
        # Check Presigned URL query params
        if "X-Amz-Signature" in request.GET:
            return self._verify_presigned_auth(request, secret_key, payload_hash)

        # Unauthenticated request
        return False

    @classmethod
    def _verify_header_auth(
        cls,
        request,
        auth_header: str,
        secret_key: str,
        payload_hash: Optional[str] = None,
    ) -> bool:
        parsed = cls.parse_auth_header(auth_header)
        credential = parsed.get("Credential")
        signed_headers_str = parsed.get("SignedHeaders")
        signature = parsed.get("Signature")

        if not credential or not signed_headers_str or not signature:
            raise SignatureDoesNotMatchError("Malformed Authorization header.")

        cred_parts = credential.split("/")
        if len(cred_parts) < 5:
            raise SignatureDoesNotMatchError("Malformed Credential component in Authorization header.")

        access_key, date_stamp, region, service, _ = cred_parts[:5]
        amz_date = request.headers.get("x-amz-date") or request.headers.get("X-Amz-Date")
        if not amz_date:
            amz_date = request.headers.get("Date") or request.headers.get("date")

        signed_headers = [h.strip().lower() for h in signed_headers_str.split(";")]

        # Canonical URI
        canonical_uri = urllib.parse.quote(request.path, safe="/")

        # Canonical Query String
        query_params = []
        for k in sorted(request.GET.keys()):
            for v in sorted(request.GET.getlist(k)):
                query_params.append(
                    f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
                )
        canonical_query_string = "&".join(query_params)

        # Canonical Headers
        canonical_headers_list = []
        for h in signed_headers:
            val = request.headers.get(h)
            if val is None:
                val = request.META.get(f"HTTP_{h.upper().replace('-', '_')}", "")
            # Normalize whitespace
            val_clean = " ".join(val.strip().split())
            canonical_headers_list.append(f"{h}:{val_clean}\n")
        canonical_headers = "".join(canonical_headers_list)

        # Payload Hash
        if not payload_hash:
            payload_hash = request.headers.get("x-amz-content-sha256") or "UNSIGNED-PAYLOAD"

        canonical_request = "\n".join([
            request.method.upper(),
            canonical_uri,
            canonical_query_string,
            canonical_headers,
            signed_headers_str,
            payload_hash,
        ])

        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()

        # String to sign
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = "\n".join([
            algorithm,
            amz_date or date_stamp,
            credential_scope,
            hashed_canonical_request,
        ])

        signing_key = get_signature_key(secret_key, date_stamp, region, service)
        expected_signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            raise SignatureDoesNotMatchError()

        return True

    @classmethod
    def _verify_presigned_auth(
        cls,
        request,
        secret_key: str,
        payload_hash: Optional[str] = None,
    ) -> bool:
        signature = request.GET.get("X-Amz-Signature")
        algorithm = request.GET.get("X-Amz-Algorithm")
        credential = request.GET.get("X-Amz-Credential")
        amz_date = request.GET.get("X-Amz-Date")
        expires = request.GET.get("X-Amz-Expires")
        signed_headers_str = request.GET.get("X-Amz-SignedHeaders")

        if not signature or not credential or not amz_date or not signed_headers_str:
            raise SignatureDoesNotMatchError("Missing required presigned URL parameters.")

        cred_parts = credential.split("/")
        access_key, date_stamp, region, service, _ = cred_parts[:5]

        signed_headers = [h.strip().lower() for h in signed_headers_str.split(";")]

        canonical_uri = urllib.parse.quote(request.path, safe="/")

        # Query params excluding X-Amz-Signature
        query_params = []
        for k in sorted(request.GET.keys()):
            if k == "X-Amz-Signature":
                continue
            for v in sorted(request.GET.getlist(k)):
                query_params.append(
                    f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
                )
        canonical_query_string = "&".join(query_params)

        canonical_headers_list = []
        for h in signed_headers:
            val = request.headers.get(h)
            if val is None:
                val = request.META.get(f"HTTP_{h.upper().replace('-', '_')}", "")
            val_clean = " ".join(val.strip().split())
            canonical_headers_list.append(f"{h}:{val_clean}\n")
        canonical_headers = "".join(canonical_headers_list)

        payload_hash = payload_hash or "UNSIGNED-PAYLOAD"

        canonical_request = "\n".join([
            request.method.upper(),
            canonical_uri,
            canonical_query_string,
            canonical_headers,
            signed_headers_str,
            payload_hash,
        ])

        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = "\n".join([
            algorithm,
            amz_date,
            credential_scope,
            hashed_canonical_request,
        ])

        signing_key = get_signature_key(secret_key, date_stamp, region, service)
        expected_signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            raise SignatureDoesNotMatchError("Presigned signature does not match.")

        return True
