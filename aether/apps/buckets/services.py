"""Bucket Domain Service handling business logic for S3 Buckets."""

import re
from typing import List, Optional
from django.db import transaction

from aether.apps.auth.models import User
from aether.apps.buckets.models import Bucket
from aether.core.exceptions import (
    BucketAlreadyExistsError,
    BucketNotEmptyError,
    InvalidBucketNameError,
    NoSuchBucketError,
)
from aether.storage.factory import get_storage_driver

BUCKET_NAME_REGEX = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")


class BucketService:
    """Service layer managing S3 bucket operations."""

    @staticmethod
    def validate_bucket_name(name: str) -> None:
        if not BUCKET_NAME_REGEX.match(name) or ".." in name or ".-" in name or "-." in name:
            raise InvalidBucketNameError(f"Bucket name '{name}' does not follow S3 naming conventions.")

    @classmethod
    def create_bucket(cls, name: str, owner: User) -> Bucket:
        cls.validate_bucket_name(name)

        if Bucket.objects.filter(name=name).exists():
            raise BucketAlreadyExistsError(f"Bucket '{name}' already exists.")

        with transaction.atomic():
            bucket = Bucket.objects.create(name=name, owner=owner)
            storage_driver = get_storage_driver()
            storage_driver.create_bucket_storage(name)

        return bucket

    @classmethod
    def get_bucket(cls, name: str) -> Bucket:
        try:
            return Bucket.objects.get(name=name)
        except Bucket.DoesNotExist:
            raise NoSuchBucketError(f"Bucket '{name}' does not exist.", resource=f"/{name}")

    @classmethod
    def list_buckets(cls, owner: Optional[User] = None) -> List[Bucket]:
        queryset = Bucket.objects.all()
        if owner:
            queryset = queryset.filter(owner=owner)
        return list(queryset)

    @classmethod
    def delete_bucket(cls, name: str, owner: Optional[User] = None) -> None:
        bucket = cls.get_bucket(name)

        # Import Object model lazily to avoid circular dependencies
        from aether.apps.objects.models import Object
        if Object.objects.filter(bucket=bucket).exists():
            raise BucketNotEmptyError(f"Bucket '{name}' is not empty.", resource=f"/{name}")

        with transaction.atomic():
            bucket.delete()
            storage_driver = get_storage_driver()
            storage_driver.delete_bucket_storage(name)
