"""Future Azure Blob Storage driver placeholder for pluggable backends."""

from typing import BinaryIO, Generator, Iterable, Optional, Tuple

from aether.storage.drivers.base import BaseStorageDriver


class FutureAzureDriver(BaseStorageDriver):
    """Placeholder driver for proxying object storage to Azure Blob Storage."""

    def __init__(self, account_name: str = "defaultaccount"):
        self.account_name = account_name

    def save(
        self,
        bucket: str,
        key: str,
        data: BinaryIO | bytes | Iterable[bytes],
        chunk_size: int = 65536,
    ) -> Tuple[int, str]:
        raise NotImplementedError("FutureAzureDriver is a placeholder for Azure backends.")

    def read(
        self,
        bucket: str,
        key: str,
        range_start: Optional[int] = None,
        range_end: Optional[int] = None,
        chunk_size: int = 65536,
    ) -> Generator[bytes, None, None]:
        raise NotImplementedError("FutureAzureDriver is a placeholder for Azure backends.")

    def delete(self, bucket: str, key: str) -> bool:
        raise NotImplementedError("FutureAzureDriver is a placeholder for Azure backends.")

    def exists(self, bucket: str, key: str) -> bool:
        raise NotImplementedError("FutureAzureDriver is a placeholder for Azure backends.")

    def list(self, bucket: str, prefix: str = "") -> list[str]:
        raise NotImplementedError("FutureAzureDriver is a placeholder for Azure backends.")

    def size(self, bucket: str, key: str) -> int:
        raise NotImplementedError("FutureAzureDriver is a placeholder for Azure backends.")

    def copy(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> Tuple[int, str]:
        raise NotImplementedError("FutureAzureDriver is a placeholder for Azure backends.")

    def move(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> Tuple[int, str]:
        raise NotImplementedError("FutureAzureDriver is a placeholder for Azure backends.")

    def create_bucket_storage(self, bucket: str) -> bool:
        raise NotImplementedError("FutureAzureDriver is a placeholder for Azure backends.")

    def delete_bucket_storage(self, bucket: str) -> bool:
        raise NotImplementedError("FutureAzureDriver is a placeholder for Azure backends.")
