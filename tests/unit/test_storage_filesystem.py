"""Unit tests for Filesystem Storage Driver."""

import pytest
import shutil
from pathlib import Path
from aether.storage.drivers.filesystem import FilesystemDriver


@pytest.fixture
def tmp_storage(tmp_path):
    storage_dir = tmp_path / "storage_root"
    driver = FilesystemDriver(base_dir=storage_dir)
    yield driver
    if storage_dir.exists():
        shutil.rmtree(storage_dir)


def test_filesystem_driver_save_and_read(tmp_storage):
    driver = tmp_storage
    bucket = "test-bucket"
    driver.create_bucket_storage(bucket)

    data = b"Hello, Aether Object Storage!"
    size, etag = driver.save(bucket, "hello.txt", data)

    assert size == len(data)
    assert etag is not None
    assert driver.exists(bucket, "hello.txt")
    assert driver.size(bucket, "hello.txt") == len(data)

    content = b"".join(driver.read(bucket, "hello.txt"))
    assert content == data


def test_filesystem_driver_range_read(tmp_storage):
    driver = tmp_storage
    bucket = "range-bucket"
    driver.create_bucket_storage(bucket)

    data = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    driver.save(bucket, "data.txt", data)

    # Read range 0-9
    range_data = b"".join(driver.read(bucket, "data.txt", range_start=0, range_end=9))
    assert range_data == b"0123456789"

    # Read range 10-15
    range_data2 = b"".join(driver.read(bucket, "data.txt", range_start=10, range_end=15))
    assert range_data2 == b"ABCDEF"


def test_filesystem_driver_copy_and_move(tmp_storage):
    driver = tmp_storage
    src_bucket, dest_bucket = "src-b", "dest-b"
    driver.create_bucket_storage(src_bucket)
    driver.create_bucket_storage(dest_bucket)

    driver.save(src_bucket, "file.txt", b"Copy content")

    # Copy
    driver.copy(src_bucket, "file.txt", dest_bucket, "copied.txt")
    assert driver.exists(dest_bucket, "copied.txt")
    assert driver.exists(src_bucket, "file.txt")

    # Move
    driver.move(src_bucket, "file.txt", dest_bucket, "moved.txt")
    assert driver.exists(dest_bucket, "moved.txt")
    assert not driver.exists(src_bucket, "file.txt")


def test_filesystem_driver_path_traversal_prevention(tmp_storage):
    driver = tmp_storage
    bucket = "secure-bucket"
    driver.create_bucket_storage(bucket)

    with pytest.raises(ValueError):
        driver.save(bucket, "../../../etc/passwd", b"malicious")
