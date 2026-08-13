"""Storage Factory for instantiating configured Storage Driver."""

import os
from pathlib import Path

from django.conf import settings

from aether.storage.drivers.base import BaseStorageDriver
from aether.storage.drivers.filesystem import FilesystemDriver
from aether.storage.drivers.future_azure import FutureAzureDriver
from aether.storage.drivers.future_gcs import FutureGCSDriver
from aether.storage.drivers.future_s3 import FutureS3Driver

_DRIVER_INSTANCE: BaseStorageDriver | None = None


def get_storage_driver() -> BaseStorageDriver:
    """Factory function returning the active storage driver instance."""
    global _DRIVER_INSTANCE
    if _DRIVER_INSTANCE is not None:
        return _DRIVER_INSTANCE

    driver_type = getattr(settings, "STORAGE_DRIVER", os.getenv("STORAGE_DRIVER", "filesystem"))
    storage_root = getattr(settings, "STORAGE_ROOT", os.getenv("STORAGE_ROOT", "/tmp/aether_storage"))

    if driver_type == "filesystem":
        _DRIVER_INSTANCE = FilesystemDriver(base_dir=storage_root)
    elif driver_type == "s3":
        _DRIVER_INSTANCE = FutureS3Driver()
    elif driver_type == "gcs":
        _DRIVER_INSTANCE = FutureGCSDriver()
    elif driver_type == "azure":
        _DRIVER_INSTANCE = FutureAzureDriver()
    else:
        raise ValueError(f"Unsupported STORAGE_DRIVER: {driver_type}")

    return _DRIVER_INSTANCE


def reset_storage_driver() -> None:
    """Reset cached storage driver singleton (useful for testing)."""
    global _DRIVER_INSTANCE
    _DRIVER_INSTANCE = None
