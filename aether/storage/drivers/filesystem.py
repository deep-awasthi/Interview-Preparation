"""Filesystem Storage Driver implementation for Aether."""

import hashlib
import os
import shutil
from pathlib import Path
from typing import BinaryIO, Generator, Iterable, Optional, Tuple

from aether.storage.drivers.base import BaseStorageDriver


class FilesystemDriver(BaseStorageDriver):
    """Local filesystem storage engine.

    Stores objects on disk under a base directory structured as:
    <base_dir>/<bucket>/<sanitized_key>
    """

    def __init__(self, base_dir: str | Path = "/tmp/aether_storage"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, bucket: str, key: str) -> Path:
        """Resolve and sanitize file path within bucket directory, preventing path traversal."""
        bucket_dir = (self.base_dir / bucket).resolve()
        # Prevent escaping the base_dir
        if not str(bucket_dir).startswith(str(self.base_dir)):
            raise ValueError(f"Invalid bucket path traversal attempt: {bucket}")

        # Standardize key path
        clean_key = os.path.normpath(key).lstrip("/")
        file_path = (bucket_dir / clean_key).resolve()

        if not str(file_path).startswith(str(bucket_dir)):
            raise ValueError(f"Path traversal detected for key: {key}")

        return file_path

    def save(
        self,
        bucket: str,
        key: str,
        data: BinaryIO | bytes | Iterable[bytes],
        chunk_size: int = 65536,
    ) -> Tuple[int, str]:
        file_path = self._resolve_path(bucket, key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        md5 = hashlib.md5()
        total_bytes = 0

        # Write via temporary file for atomic operations
        temp_path = file_path.with_suffix(".tmp_" + os.urandom(4).hex())

        try:
            with open(temp_path, "wb") as f:
                if isinstance(data, bytes):
                    f.write(data)
                    md5.update(data)
                    total_bytes = len(data)
                elif hasattr(data, "read"):
                    while True:
                        chunk = data.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        md5.update(chunk)
                        total_bytes += len(chunk)
                elif isinstance(data, Iterable):
                    for chunk in data:
                        f.write(chunk)
                        md5.update(chunk)
                        total_bytes += len(chunk)
                else:
                    raise TypeError("Unsupported data type for storage save")

            os.replace(temp_path, file_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

        etag = md5.hexdigest()
        return total_bytes, etag

    def read(
        self,
        bucket: str,
        key: str,
        range_start: Optional[int] = None,
        range_end: Optional[int] = None,
        chunk_size: int = 65536,
    ) -> Generator[bytes, None, None]:
        file_path = self._resolve_path(bucket, key)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Object not found: {bucket}/{key}")

        file_size = file_path.stat().st_size

        start = 0 if range_start is None else max(0, range_start)
        end = file_size - 1 if range_end is None else min(file_size - 1, range_end)

        if start > end or start >= file_size:
            return

        bytes_to_read = end - start + 1

        with open(file_path, "rb") as f:
            f.seek(start)
            bytes_remaining = bytes_to_read
            while bytes_remaining > 0:
                current_chunk_size = min(chunk_size, bytes_remaining)
                chunk = f.read(current_chunk_size)
                if not chunk:
                    break
                bytes_remaining -= len(chunk)
                yield chunk

    def delete(self, bucket: str, key: str) -> bool:
        try:
            file_path = self._resolve_path(bucket, key)
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                # Clean up empty parent directories if any
                parent = file_path.parent
                bucket_dir = (self.base_dir / bucket).resolve()
                while parent != bucket_dir and parent.exists():
                    if not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break
                return True
        except FileNotFoundError:
            pass
        return False

    def exists(self, bucket: str, key: str) -> bool:
        try:
            file_path = self._resolve_path(bucket, key)
            return file_path.exists() and file_path.is_file()
        except ValueError:
            return False

    def list(self, bucket: str, prefix: str = "") -> list[str]:
        bucket_dir = (self.base_dir / bucket).resolve()
        if not bucket_dir.exists() or not bucket_dir.is_dir():
            return []

        clean_prefix = prefix.lstrip("/")
        keys = []
        for root, _, files in os.walk(bucket_dir):
            for file in files:
                if file.startswith(".tmp_"):
                    continue
                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(bucket_dir)).replace("\\", "/")
                if rel_path.startswith(clean_prefix):
                    keys.append(rel_path)

        return sorted(keys)

    def size(self, bucket: str, key: str) -> int:
        file_path = self._resolve_path(bucket, key)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Object not found: {bucket}/{key}")
        return file_path.stat().st_size

    def copy(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> Tuple[int, str]:
        src_path = self._resolve_path(src_bucket, src_key)
        if not src_path.exists():
            raise FileNotFoundError(f"Source object not found: {src_bucket}/{src_key}")

        with open(src_path, "rb") as f:
            return self.save(dest_bucket, dest_key, f)

    def move(
        self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str
    ) -> Tuple[int, str]:
        res = self.copy(src_bucket, src_key, dest_bucket, dest_key)
        self.delete(src_bucket, src_key)
        return res

    def create_bucket_storage(self, bucket: str) -> bool:
        bucket_dir = (self.base_dir / bucket).resolve()
        bucket_dir.mkdir(parents=True, exist_ok=True)
        return True

    def delete_bucket_storage(self, bucket: str) -> bool:
        bucket_dir = (self.base_dir / bucket).resolve()
        if bucket_dir.exists() and bucket_dir.is_dir():
            shutil.rmtree(bucket_dir)
            return True
        return False
