"""Base Abstract Storage Driver interface for Aether Object Storage."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Generator, Iterable, Optional, Tuple


class BaseStorageDriver(ABC):
    """Abstract interface defining the contract for all object storage backends."""

    @abstractmethod
    def save(
        self,
        bucket: str,
        key: str,
        data: BinaryIO | bytes | Iterable[bytes],
        chunk_size: int = 65536,
    ) -> Tuple[int, str]:
        """Save object binary payload to backend storage.

        Args:
            bucket: Name of the target bucket.
            key: Object key/path.
            data: Binary payload as file-like object, bytes, or byte generator.
            chunk_size: Size of chunks for streaming writes.

        Returns:
            Tuple of (total_bytes_written, etag_md5_hex)
        """
        pass

    @abstractmethod
    def read(
        self,
        bucket: str,
        key: str,
        range_start: Optional[int] = None,
        range_end: Optional[int] = None,
        chunk_size: int = 65536,
    ) -> Generator[bytes, None, None]:
        """Stream object binary data from backend storage with optional range support.

        Args:
            bucket: Name of the bucket.
            key: Object key.
            range_start: Optional byte offset start (inclusive).
            range_end: Optional byte offset end (inclusive).
            chunk_size: Size of each streamed chunk.

        Yields:
            Chunks of bytes.
        """
        pass

    @abstractmethod
    def delete(self, bucket: str, key: str) -> bool:
        """Delete an object from backend storage.

        Args:
            bucket: Bucket name.
            key: Object key.

        Returns:
            True if deleted, False if object did not exist.
        """
        pass

    @abstractmethod
    def exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in backend storage."""
        pass

    @abstractmethod
    def list(self, bucket: str, prefix: str = "") -> list[str]:
        """List keys in a bucket starting with prefix."""
        pass

    @abstractmethod
    def size(self, bucket: str, key: str) -> int:
        """Get object size in bytes from backend storage."""
        pass

    @abstractmethod
    def copy(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> Tuple[int, str]:
        """Copy object from source to destination.

        Returns:
            Tuple of (size, etag_md5_hex)
        """
        pass

    @abstractmethod
    def move(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> Tuple[int, str]:
        """Move object from source to destination."""
        pass

    @abstractmethod
    def create_bucket_storage(self, bucket: str) -> bool:
        """Initialize storage container/directory for a bucket."""
        pass

    @abstractmethod
    def delete_bucket_storage(self, bucket: str) -> bool:
        """Remove storage container/directory for a bucket."""
        pass
