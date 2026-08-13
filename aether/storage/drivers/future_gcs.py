"""Future Google Cloud Storage driver placeholder for pluggable backends."""

from typing import BinaryIO, Generator, Iterable, Optional, Tuple

from aether.storage.drivers.base import BaseStorageDriver


class FutureGCSDriver(BaseStorageDriver):
    """Placeholder driver for proxying object storage to Google Cloud Storage (GCS)."""

    def __init__(self, project_id: str = "default-project"):
        self.project_id = project_id

    def save(
        self,
        bucket: str,
        key: str,
        data: BinaryIO | bytes | Iterable[bytes],
        chunk_size: int = 65536,
    ) -> Tuple[int, str]:
        raise NotImplementedError("FutureGCSDriver is a placeholder for GCS backends.")

    def read(
        self,
        bucket: str,
        key: str,
        range_start: Optional[int] = None,
        range_end: Optional[int] = None,
        chunk_size: int = 65536,
    ) -> Generator[bytes, None, None]:
        raise NotImplementedError("FutureGCSDriver is a placeholder for GCS backends.")

    def delete(self, bucket: str, key: str) -> bool:
        raise NotImplementedError("FutureGCSDriver is a placeholder for GCS backends.")

    def exists(self, bucket: str, key: str) -> bool:
        raise NotImplementedError("FutureGCSDriver is a placeholder for GCS backends.")

    def list(self, bucket: str, prefix: str = "") -> list[str]:
        raise NotImplementedError("FutureGCSDriver is a placeholder for GCS backends.")

    def size(self, bucket: str, key: str) -> int:
        raise NotImplementedError("FutureGCSDriver is a placeholder for GCS backends.")

    def copy(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> Tuple[int, str]:
        raise NotImplementedError("FutureGCSDriver is a placeholder for GCS backends.")

    def move(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> Tuple[int, str]:
        raise NotImplementedError("FutureGCSDriver is a placeholder for GCS backends.")

    def create_bucket_storage(self, bucket: str) -> bool:
        raise NotImplementedError("FutureGCSDriver is a placeholder for GCS backends.")

    def delete_bucket_storage(self, bucket: str) -> bool:
        raise NotImplementedError("FutureGCSDriver is a placeholder for GCS backends.")
