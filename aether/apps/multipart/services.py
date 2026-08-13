"""Multipart Upload Domain Service for S3 Multipart API."""

import uuid
import hashlib
from typing import BinaryIO, Dict, Iterable, List, Tuple
from django.db import transaction

from aether.apps.buckets.services import BucketService
from aether.apps.multipart.models import MultipartPart, MultipartUpload
from aether.apps.objects.models import Object
from aether.apps.objects.services import ObjectService
from aether.core.exceptions import NoSuchUploadError
from aether.storage.factory import get_storage_driver


class MultipartService:
    """Service layer managing S3 multipart upload lifecycles."""

    @classmethod
    def initiate_multipart_upload(
        cls, bucket_name: str, key: str, content_type: str = "application/octet-stream", metadata: Dict = None
    ) -> MultipartUpload:
        bucket = BucketService.get_bucket(bucket_name)
        upload_id = uuid.uuid4().hex

        upload = MultipartUpload.objects.create(
            upload_id=upload_id,
            bucket=bucket,
            key=key,
            content_type=content_type or "application/octet-stream",
            metadata_json=metadata or {},
        )
        return upload

    @classmethod
    def get_upload(cls, bucket_name: str, upload_id: str) -> MultipartUpload:
        try:
            return MultipartUpload.objects.get(
                bucket__name=bucket_name, upload_id=upload_id, status="IN_PROGRESS"
            )
        except MultipartUpload.DoesNotExist:
            raise NoSuchUploadError(
                f"The specified upload '{upload_id}' does not exist.",
                resource=f"/{bucket_name}",
            )

    @classmethod
    def upload_part(
        cls,
        bucket_name: str,
        key: str,
        upload_id: str,
        part_number: int,
        data: BinaryIO | bytes | Iterable[bytes],
    ) -> MultipartPart:
        upload = cls.get_upload(bucket_name, upload_id)
        storage_driver = get_storage_driver()

        temp_part_key = f".mp_uploads/{upload_id}/part_{part_number}"
        size, etag = storage_driver.save(bucket_name, temp_part_key, data)

        part, _ = MultipartPart.objects.update_or_create(
            upload=upload,
            part_number=part_number,
            defaults={"etag": etag, "size": size},
        )

        return part

    @classmethod
    def list_parts(cls, bucket_name: str, upload_id: str) -> List[MultipartPart]:
        upload = cls.get_upload(bucket_name, upload_id)
        return list(upload.parts.all().order_by("part_number"))

    @classmethod
    def complete_multipart_upload(
        cls,
        bucket_name: str,
        key: str,
        upload_id: str,
        parts_spec: List[Dict[str, Any]] = None,
    ) -> Object:
        upload = cls.get_upload(bucket_name, upload_id)
        storage_driver = get_storage_driver()

        db_parts = list(upload.parts.all().order_by("part_number"))
        if not db_parts:
            raise NoSuchUploadError("No parts uploaded for this multipart upload.")

        # Stream and concatenate all parts into final location
        def part_stream_generator():
            for p in db_parts:
                part_key = f".mp_uploads/{upload_id}/part_{p.part_number}"
                for chunk in storage_driver.read(bucket_name, part_key):
                    yield chunk

        # Save final stitched binary
        total_size, final_etag = storage_driver.save(bucket_name, key, part_stream_generator())

        # Create final object in database
        obj = ObjectService.put_object(
            bucket_name=bucket_name,
            key=key,
            data=storage_driver.read(bucket_name, key),
            content_type=upload.content_type,
            metadata=upload.metadata_json,
        )

        # Cleanup temporary part files
        for p in db_parts:
            part_key = f".mp_uploads/{upload_id}/part_{p.part_number}"
            storage_driver.delete(bucket_name, part_key)

        upload.status = "COMPLETED"
        upload.save()

        return obj

    @classmethod
    def abort_multipart_upload(cls, bucket_name: str, upload_id: str) -> None:
        upload = cls.get_upload(bucket_name, upload_id)
        storage_driver = get_storage_driver()

        db_parts = list(upload.parts.all())
        for p in db_parts:
            part_key = f".mp_uploads/{upload_id}/part_{p.part_number}"
            storage_driver.delete(bucket_name, part_key)

        upload.status = "ABORTED"
        upload.save()
