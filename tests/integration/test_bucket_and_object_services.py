"""Integration tests for BucketService, ObjectService, and MultipartService."""

import pytest
from aether.apps.auth.services import AuthService
from aether.apps.buckets.services import BucketService
from aether.apps.multipart.services import MultipartService
from aether.apps.objects.services import ObjectService
from aether.core.exceptions import BucketAlreadyExistsError, NoSuchBucketError, NoSuchKeyError


@pytest.mark.django_db
def test_bucket_service_lifecycle():
    user, _, _ = AuthService.create_user_with_credentials("testuser", "user@test.com")

    # Create bucket
    bucket = BucketService.create_bucket("integration-bucket", owner=user)
    assert bucket.name == "integration-bucket"

    # Duplicate bucket creation fails
    with pytest.raises(BucketAlreadyExistsError):
        BucketService.create_bucket("integration-bucket", owner=user)

    # Get bucket
    fetched = BucketService.get_bucket("integration-bucket")
    assert fetched.id == bucket.id

    # List buckets
    buckets = BucketService.list_buckets()
    assert len(buckets) == 1

    # Delete bucket
    BucketService.delete_bucket("integration-bucket")
    with pytest.raises(NoSuchBucketError):
        BucketService.get_bucket("integration-bucket")


@pytest.mark.django_db
def test_object_service_crud():
    user, _, _ = AuthService.create_user_with_credentials("objuser", "obj@test.com")
    BucketService.create_bucket("obj-bucket", owner=user)

    # Upload
    payload = b"Sample object binary data"
    obj = ObjectService.put_object("obj-bucket", "docs/sample.txt", payload, content_type="text/plain")
    assert obj.key == "docs/sample.txt"
    assert obj.size == len(payload)

    # Metadata
    meta = ObjectService.get_object_metadata("obj-bucket", "docs/sample.txt")
    assert meta.etag == obj.etag

    # Stream
    _, stream, _ = ObjectService.get_object_stream("obj-bucket", "docs/sample.txt")
    content = b"".join(stream)
    assert content == payload

    # List objects
    objs, prefixes, is_truncated, _ = ObjectService.list_objects("obj-bucket", prefix="docs/", delimiter="/")
    assert len(objs) == 1
    assert objs[0].key == "docs/sample.txt"

    # Delete
    ObjectService.delete_object("obj-bucket", "docs/sample.txt")
    with pytest.raises(NoSuchKeyError):
        ObjectService.get_object_metadata("obj-bucket", "docs/sample.txt")


@pytest.mark.django_db
def test_multipart_service_workflow():
    user, _, _ = AuthService.create_user_with_credentials("mpuser", "mp@test.com")
    BucketService.create_bucket("mp-bucket", owner=user)

    # Initiate
    upload = MultipartService.initiate_multipart_upload("mp-bucket", "large-video.mp4")
    upload_id = upload.upload_id

    # Upload Parts
    part1 = MultipartService.upload_part("mp-bucket", "large-video.mp4", upload_id, 1, b"PART1_BYTES_CHUNK")
    part2 = MultipartService.upload_part("mp-bucket", "large-video.mp4", upload_id, 2, b"PART2_BYTES_CHUNK")

    parts = MultipartService.list_parts("mp-bucket", upload_id)
    assert len(parts) == 2
    assert parts[0].part_number == 1
    assert parts[1].part_number == 2

    # Complete
    completed_obj = MultipartService.complete_multipart_upload("mp-bucket", "large-video.mp4", upload_id)
    assert completed_obj.key == "large-video.mp4"
    assert completed_obj.size == len(b"PART1_BYTES_CHUNKPART2_BYTES_CHUNK")
