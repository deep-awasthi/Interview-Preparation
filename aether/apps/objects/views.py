"""Plain Django Views handling S3 Object and Multipart REST operations."""

import xml.etree.ElementTree as ET
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from aether.apps.auth.services import AuthService
from aether.apps.buckets.views import _authenticate_request
from aether.apps.multipart.services import MultipartService
from aether.apps.objects.services import ObjectService
from aether.core.exceptions import S3Error
from aether.core.utils import format_s3_date
from aether.core.xml import (
    serialize_complete_multipart_upload_result,
    serialize_copy_object_result,
    serialize_initiate_multipart_upload_result,
    serialize_list_parts_result,
)


@method_decorator(csrf_exempt, name="dispatch")
class S3ObjectView(View):
    """Handler for S3 Object and Multipart REST operations."""

    def get(self, request, bucket_name, object_key):
        _authenticate_request(request)

        # Check if List Parts request (?uploadId=...)
        upload_id = request.GET.get("uploadId")
        if upload_id and "uploads" not in request.GET:
            parts = MultipartService.list_parts(bucket_name, upload_id)
            xml_data = serialize_list_parts_result(bucket_name, object_key, upload_id, parts)
            return HttpResponse(xml_data, content_type="application/xml", status=200)

        # Standard GET Object download
        version_id = request.GET.get("versionId")
        range_header = request.headers.get("Range") or request.META.get("HTTP_RANGE")

        obj, stream, range_tuple = ObjectService.get_object_stream(
            bucket_name=bucket_name,
            key=object_key,
            range_header=range_header,
            version_id=version_id,
        )

        status_code = 206 if range_tuple else 200
        response = StreamingHttpResponse(stream, status=status_code, content_type=obj.content_type)

        response["ETag"] = f'"{obj.etag}"' if not obj.etag.startswith('"') else obj.etag
        response["Last-Modified"] = format_s3_date(obj.last_modified)
        response["Accept-Ranges"] = "bytes"
        response["x-amz-request-id"] = "aether-req-0000"

        if obj.content_disposition:
            response["Content-Disposition"] = obj.content_disposition

        if range_tuple:
            start, end = range_tuple
            length = end - start + 1
            response["Content-Range"] = f"bytes {start}-{end}/{obj.size}"
            response["Content-Length"] = str(length)
        else:
            response["Content-Length"] = str(obj.size)

        return response

    def head(self, request, bucket_name, object_key):
        _authenticate_request(request)
        version_id = request.GET.get("versionId")

        obj = ObjectService.get_object_metadata(bucket_name, object_key, version_id=version_id)
        response = HttpResponse(status=200, content_type=obj.content_type)
        response["Content-Length"] = str(obj.size)
        response["ETag"] = f'"{obj.etag}"' if not obj.etag.startswith('"') else obj.etag
        response["Last-Modified"] = format_s3_date(obj.last_modified)
        response["Accept-Ranges"] = "bytes"
        response["x-amz-request-id"] = "aether-req-0000"

        if obj.content_disposition:
            response["Content-Disposition"] = obj.content_disposition

        return response

    def put(self, request, bucket_name, object_key):
        _authenticate_request(request)

        upload_id = request.GET.get("uploadId")
        part_number = request.GET.get("partNumber")

        # 1. Upload Part (?uploadId=...&partNumber=...)
        if upload_id and part_number:
            part = MultipartService.upload_part(
                bucket_name=bucket_name,
                key=object_key,
                upload_id=upload_id,
                part_number=int(part_number),
                data=request,
            )
            response = HttpResponse(status=200)
            response["ETag"] = f'"{part.etag}"' if not part.etag.startswith('"') else part.etag
            return response

        # 2. Copy Object (x-amz-copy-source header)
        copy_source = request.headers.get("x-amz-copy-source") or request.META.get("HTTP_X_AMZ_COPY_SOURCE")
        if copy_source:
            clean_source = copy_source.lstrip("/")
            src_bucket, src_key = clean_source.split("/", 1)
            dest_obj = ObjectService.copy_object(src_bucket, src_key, bucket_name, object_key)
            xml_data = serialize_copy_object_result(dest_obj.etag, dest_obj.last_modified)
            return HttpResponse(xml_data, content_type="application/xml", status=200)

        # 3. Standard Put Object upload
        content_type = request.headers.get("Content-Type", "application/octet-stream")
        content_disposition = request.headers.get("Content-Disposition")

        obj = ObjectService.put_object(
            bucket_name=bucket_name,
            key=object_key,
            data=request,
            content_type=content_type,
            content_disposition=content_disposition,
        )

        response = HttpResponse(status=200)
        response["ETag"] = f'"{obj.etag}"' if not obj.etag.startswith('"') else obj.etag
        return response

    def post(self, request, bucket_name, object_key):
        _authenticate_request(request)

        # 1. Initiate Multipart Upload (?uploads)
        if "uploads" in request.GET:
            content_type = request.headers.get("Content-Type", "application/octet-stream")
            upload = MultipartService.initiate_multipart_upload(
                bucket_name=bucket_name, key=object_key, content_type=content_type
            )
            xml_data = serialize_initiate_multipart_upload_result(
                bucket_name, object_key, upload.upload_id
            )
            return HttpResponse(xml_data, content_type="application/xml", status=200)

        # 2. Complete Multipart Upload (?uploadId=...)
        upload_id = request.GET.get("uploadId")
        if upload_id:
            obj = MultipartService.complete_multipart_upload(
                bucket_name=bucket_name, key=object_key, upload_id=upload_id
            )
            xml_data = serialize_complete_multipart_upload_result(
                bucket_name, object_key, obj.etag
            )
            return HttpResponse(xml_data, content_type="application/xml", status=200)

        return HttpResponse(status=400)

    def delete(self, request, bucket_name, object_key):
        _authenticate_request(request)

        upload_id = request.GET.get("uploadId")

        # 1. Abort Multipart Upload (?uploadId=...)
        if upload_id:
            MultipartService.abort_multipart_upload(bucket_name, upload_id)
            return HttpResponse(status=204)

        # 2. Standard Delete Object
        version_id = request.GET.get("versionId")
        ObjectService.delete_object(bucket_name, object_key, version_id=version_id)

        response = HttpResponse(status=204)
        return response
