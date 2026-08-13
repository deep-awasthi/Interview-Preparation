"""Object Domain Service handling business logic for Object storage and retrieval."""

import uuid
from datetime import datetime, timezone
from typing import Any, BinaryIO, Generator, Iterable, List, Optional, Tuple
from django.db import transaction

from aether.apps.buckets.models import Bucket
from aether.apps.buckets.services import BucketService
from aether.apps.objects.models import Object
from aether.core.exceptions import (
    InvalidRangeError,
    NoSuchBucketError,
    NoSuchKeyError,
)
from aether.core.utils import parse_range_header
from aether.storage.factory import get_storage_driver


class ObjectService:
    """Service layer managing Object uploads, downloads, copies, deletes, and listing."""

    @classmethod
    def put_object(
        cls,
        bucket_name: str,
        key: str,
        data: BinaryIO | bytes | Iterable[bytes],
        content_type: str = "application/octet-stream",
        content_disposition: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Object:
        bucket = BucketService.get_bucket(bucket_name)

        storage_driver = get_storage_driver()
        size, etag = storage_driver.save(bucket_name, key, data)

        version_id = "null"
        if bucket.versioning_enabled:
            version_id = uuid.uuid4().hex[:16]

        with transaction.atomic():
            # Mark previous versions as not latest
            Object.objects.filter(bucket=bucket, key=key).update(is_latest=False)

            obj = Object.objects.create(
                bucket=bucket,
                key=key,
                version_id=version_id,
                is_latest=True,
                is_delete_marker=False,
                size=size,
                etag=etag,
                content_type=content_type or "application/octet-stream",
                content_disposition=content_disposition,
                metadata_json=metadata or {},
            )

        return obj

    @classmethod
    def get_object_metadata(
        cls, bucket_name: str, key: str, version_id: Optional[str] = None
    ) -> Object:
        bucket = BucketService.get_bucket(bucket_name)

        queryset = Object.objects.filter(bucket=bucket, key=key, is_delete_marker=False)
        if version_id:
            queryset = queryset.filter(version_id=version_id)
        else:
            queryset = queryset.filter(is_latest=True)

        obj = queryset.first()
        if not obj:
            raise NoSuchKeyError(f"Key '{key}' not found in bucket '{bucket_name}'.", resource=f"/{bucket_name}/{key}")

        return obj

    @classmethod
    def get_object_stream(
        cls,
        bucket_name: str,
        key: str,
        range_header: Optional[str] = None,
        version_id: Optional[str] = None,
    ) -> Tuple[Object, Generator[bytes, None, None], Optional[Tuple[int, int]]]:
        obj = cls.get_object_metadata(bucket_name, key, version_id)

        start, end = None, None
        if range_header:
            start, end = parse_range_header(range_header, obj.size)
            if start is None or end is None:
                raise InvalidRangeError("Requested range is not satisfiable.")

        storage_driver = get_storage_driver()
        stream = storage_driver.read(bucket_name, key, range_start=start, range_end=end)

        range_tuple = (start, end) if start is not None and end is not None else None
        return obj, stream, range_tuple

    @classmethod
    def delete_object(
        cls, bucket_name: str, key: str, version_id: Optional[str] = None
    ) -> bool:
        bucket = BucketService.get_bucket(bucket_name)

        if version_id:
            obj = Object.objects.filter(bucket=bucket, key=key, version_id=version_id).first()
            if obj:
                with transaction.atomic():
                    obj.delete()
                    # Check if any remaining versions exist
                    remaining = Object.objects.filter(bucket=bucket, key=key).order_by("-last_modified").first()
                    if remaining:
                        remaining.is_latest = True
                        remaining.save()
                    else:
                        storage_driver = get_storage_driver()
                        storage_driver.delete(bucket_name, key)
                return True
            return False
        else:
            # Delete latest or insert delete marker if versioning enabled
            if bucket.versioning_enabled:
                new_version_id = uuid.uuid4().hex[:16]
                with transaction.atomic():
                    Object.objects.filter(bucket=bucket, key=key).update(is_latest=False)
                    Object.objects.create(
                        bucket=bucket,
                        key=key,
                        version_id=new_version_id,
                        is_latest=True,
                        is_delete_marker=True,
                        size=0,
                        etag="",
                    )
                return True
            else:
                with transaction.atomic():
                    Object.objects.filter(bucket=bucket, key=key).delete()
                    storage_driver = get_storage_driver()
                    storage_driver.delete(bucket_name, key)
                return True

    @classmethod
    def copy_object(
        cls,
        src_bucket_name: str,
        src_key: str,
        dest_bucket_name: str,
        dest_key: str,
    ) -> Object:
        src_obj = cls.get_object_metadata(src_bucket_name, src_key)
        storage_driver = get_storage_driver()
        size, etag = storage_driver.copy(src_bucket_name, src_key, dest_bucket_name, dest_key)

        return cls.put_object(
            bucket_name=dest_bucket_name,
            key=dest_key,
            data=storage_driver.read(dest_bucket_name, dest_key),
            content_type=src_obj.content_type,
            content_disposition=src_obj.content_disposition,
            metadata=src_obj.metadata_json,
        )

    @classmethod
    def list_objects(
        cls,
        bucket_name: str,
        prefix: str = "",
        delimiter: str = "",
        max_keys: int = 1000,
        continuation_token: Optional[str] = None,
        marker: Optional[str] = None,
    ) -> Tuple[List[Object], List[str], bool, Optional[str]]:
        bucket = BucketService.get_bucket(bucket_name)

        queryset = Object.objects.filter(bucket=bucket, is_latest=True, is_delete_marker=False)

        if prefix:
            queryset = queryset.filter(key__startswith=prefix)

        start_marker = continuation_token or marker
        if start_marker:
            queryset = queryset.filter(key__gt=start_marker)

        queryset = queryset.order_by("key")

        all_objects = list(queryset[: max_keys + 1])
        is_truncated = len(all_objects) > max_keys

        objects_to_return = all_objects[:max_keys]
        common_prefixes: set[str] = set()

        final_objects: List[Object] = []

        if delimiter:
            prefix_len = len(prefix)
            for obj in objects_to_return:
                sub_key = obj.key[prefix_len:]
                if delimiter in sub_key:
                    delim_index = sub_key.find(delimiter)
                    common_prefix = prefix + sub_key[: delim_index + len(delimiter)]
                    common_prefixes.add(common_prefix)
                else:
                    final_objects.append(obj)
        else:
            final_objects = objects_to_return

        next_token = final_objects[-1].key if is_truncated and final_objects else None

        return final_objects, sorted(list(common_prefixes)), is_truncated, next_token
