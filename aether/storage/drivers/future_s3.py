"""Future AWS S3 remote storage driver placeholder for pluggable backends."""

from typing import BinaryIO, Generator, Iterable, Optional, Tuple

from aether.storage.drivers.base import BaseStorageDriver


class FutureS3Driver(BaseStorageDriver):
    """Placeholder driver for proxying object storage to remote AWS S3 buckets."""

    def __init__(self, region: str = "us-east-1"):
        self.region = region

    def save(
        self,
        bucket: str,
        key: str,
        data: BinaryIO | bytes | Iterable[bytes],
        chunk_size: int = 65536,
    ) -> Tuple[int, str]:
        raise NotImplementedError("FutureS3Driver is a placeholder for remote S3 backends.")

    def read(
        self,
        bucket: str,
        key: str,
        range_start: Optional[int] = None,
        range_end: Optional[int] = None,
        chunk_size: int = 65536,
    ) -> Generator[bytes, None, None]:
        raise NotImplementedError("FutureS3Driver is a placeholder for remote S3 backends.")

    def delete(self, bucket: str, key: str) -> bool:
        raise NotImplementedError("FutureS3Driver is a placeholder for remote S3 backends.")

    def exists(self, bucket: str, key: str) -> bool:
        raise NotImplementedError("FutureS3Driver is a placeholder for remote S3 backends.")

    def list(self, bucket: str, prefix: str = "") -> list[str]:
        raise NotImplementedError("FutureS3Driver is a placeholder for remote S3 backends.")

    def size(self, bucket: str, key: str) -> int:
        raise NotImplementedError("FutureS3Driver is a placeholder for remote S3 backends.")

    def copy(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> Tuple[int, str]:
        raise NotImplementedError("FutureS3Driver is a placeholder for remote S3 backends.")

    def move(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> Tuple[int, str]:
        raise NotImplementedError("FutureS3Driver is a placeholder for remote S3 backends.")

    def create_bucket_storage(self, bucket: str) -> bool:
        raise NotImplementedError("FutureS3Driver is a placeholder for remote S3 backends.")

    def delete_bucket_storage(self, bucket: str) -> bool:
        raise NotImplementedError("FutureS3Driver is a placeholder for remote S3 backends.")
