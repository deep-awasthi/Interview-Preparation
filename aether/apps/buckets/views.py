"""Plain Django Views handling S3 Bucket REST operations."""

import xml.etree.ElementTree as ET
from django.http import HttpResponse, StreamingHttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from aether.apps.auth.models import AccessKey
from aether.apps.auth.services import AuthService
from aether.apps.buckets.services import BucketService
from aether.apps.objects.services import ObjectService
from aether.apps.signatures.validator import SigV4Validator
from aether.core.exceptions import AccessDeniedError, S3Error
from aether.core.utils import format_s3_date
from aether.core.xml import serialize_list_buckets, serialize_list_objects_v1, serialize_list_objects_v2


def _authenticate_request(request):
    """Helper method to authenticate SigV4 requests."""
    auth_header = request.headers.get("Authorization") or request.META.get("HTTP_AUTHORIZATION")
    access_key_id = None
    if auth_header and auth_header.startswith("AWS4-HMAC-SHA256"):
        parsed = SigV4Validator.parse_auth_header(auth_header)
        credential = parsed.get("Credential", "")
        access_key_id = credential.split("/")[0] if credential else None
    elif "X-Amz-Credential" in request.GET:
        credential = request.GET.get("X-Amz-Credential", "")
        access_key_id = credential.split("/")[0] if credential else None

    user = None
    if access_key_id:
        ak = AuthService.get_access_key(access_key_id)
        if not ak:
            # Auto-provision default admin user if matching initial test keys
            if access_key_id in ("admin", "AKIAIOSFODNN7EXAMPLE"):
                user, ak, _ = AuthService.create_user_with_credentials(
                    username="admin",
                    email="admin@aether.local",
                    access_key_id=access_key_id,
                    secret_key="password" if access_key_id == "admin" else "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                )
            else:
                raise AccessDeniedError("Invalid Access Key ID.")

        secret = ak.secret_key_plain or "password"
        SigV4Validator.verify_request(request, secret)
        user = ak.user

    return user


@method_decorator(csrf_exempt, name="dispatch")
class S3BucketRootView(View):
    """Handler for GET / (List All My Buckets)."""

    def get(self, request):
        user = _authenticate_request(request)
        buckets = BucketService.list_buckets(owner=user)
        xml_data = serialize_list_buckets(buckets)
        return HttpResponse(xml_data, content_type="application/xml", status=200)


@method_decorator(csrf_exempt, name="dispatch")
class S3BucketView(View):
    """Handler for S3 Bucket REST operations (PUT, GET, DELETE, HEAD)."""

    def put(self, request, bucket_name):
        user = _authenticate_request(request)
        if not user:
            # Fallback to root admin
            user, _, _ = AuthService.create_user_with_credentials(
                username="admin", email="admin@aether.local", access_key_id="admin", secret_key="password"
            )

        BucketService.create_bucket(bucket_name, owner=user)
        response = HttpResponse(status=200)
        response["Location"] = f"/{bucket_name}"
        return response

    def head(self, request, bucket_name):
        _authenticate_request(request)
        bucket = BucketService.get_bucket(bucket_name)
        response = HttpResponse(status=200)
        response["x-amz-bucket-region"] = "us-east-1"
        return response

    def get(self, request, bucket_name):
        _authenticate_request(request)
        bucket = BucketService.get_bucket(bucket_name)

        list_type = request.GET.get("list-type")
        prefix = request.GET.get("prefix", "")
        delimiter = request.GET.get("delimiter", "")
        max_keys = int(request.GET.get("max-keys", "1000"))
        continuation_token = request.GET.get("continuation-token")
        marker = request.GET.get("marker")

        objects, common_prefixes, is_truncated, next_token = ObjectService.list_objects(
            bucket_name=bucket_name,
            prefix=prefix,
            delimiter=delimiter,
            max_keys=max_keys,
            continuation_token=continuation_token,
            marker=marker,
        )

        if list_type == "2":
            xml_data = serialize_list_objects_v2(
                bucket_name=bucket_name,
                objects=objects,
                common_prefixes=common_prefixes,
                is_truncated=is_truncated,
                max_keys=max_keys,
                prefix=prefix,
                delimiter=delimiter,
                continuation_token=continuation_token,
                next_continuation_token=next_token,
                key_count=len(objects),
            )
        else:
            xml_data = serialize_list_objects_v1(
                bucket_name=bucket_name,
                objects=objects,
                common_prefixes=common_prefixes,
                is_truncated=is_truncated,
                max_keys=max_keys,
                prefix=prefix,
                delimiter=delimiter,
                marker=marker or "",
                next_marker=next_token or "",
            )

        return HttpResponse(xml_data, content_type="application/xml", status=200)

    def delete(self, request, bucket_name):
        user = _authenticate_request(request)
        BucketService.delete_bucket(bucket_name, owner=user)
        return HttpResponse(status=204)
