"""Aether Core Middleware for S3 exception handling and host bucket resolution."""

import logging
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from aether.core.exceptions import S3Error

logger = logging.getLogger(__name__)


class S3ExceptionMiddleware(MiddlewareMixin):
    """Catch S3Error exceptions and return proper S3 XML error responses."""

    def process_exception(self, request, exception):
        if isinstance(exception, S3Error):
            logger.warning(f"S3 Exception handled: {exception.code} - {exception.message}")
            return exception.to_response()
        return None


class S3HostBucketMiddleware(MiddlewareMixin):
    """Middleware for Virtual-Host Style bucket extraction.

    For example, if host is 'mybucket.localhost:8000', attaches
    request.s3_bucket = 'mybucket'.
    """

    def process_request(self, request):
        host = request.get_host().split(":")[0]
        # Skip if host is IP address or plain localhost
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "testserver"):
            request.s3_bucket = None
            return

        parts = host.split(".")
        if len(parts) > 1:
            request.s3_bucket = parts[0]
        else:
            request.s3_bucket = None
