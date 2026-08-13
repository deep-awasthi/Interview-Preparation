"""Comprehensive S3 API Compatibility tests using standard AWS boto3 SDK."""

import boto3
import pytest
import requests
from botocore.exceptions import ClientError
from django.test import LiveServerTestCase

from aether.apps.auth.services import AuthService


@pytest.mark.django_db
class Boto3CompatibilityTest(LiveServerTestCase):
    """End-to-End AWS boto3 Client Compatibility Test Suite against live Django server."""

    def setUp(self):
        super().setUp()
        # Seed default admin user credentials
        AuthService.create_user_with_credentials(
            username="admin",
            email="admin@aether.local",
            access_key_id="admin",
            secret_key="password",
        )

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.live_server_url,
            aws_access_key_id="admin",
            aws_secret_access_key="password",
            region_name="us-east-1",
            config=boto3.session.Config(signature_version="s3v4"),
        )

    def test_full_s3_boto3_workflow(self):
        bucket_name = "boto3-test-bucket"

        # 1. Create Bucket
        res = self.s3_client.create_bucket(Bucket=bucket_name)
        assert res["ResponseMetadata"]["HTTPStatusCode"] == 200

        # 2. List Buckets
        buckets_res = self.s3_client.list_buckets()
        assert any(b["Name"] == bucket_name for b in buckets_res["Buckets"])

        # 3. Head Bucket
        head_b = self.s3_client.head_bucket(Bucket=bucket_name)
        assert head_b["ResponseMetadata"]["HTTPStatusCode"] == 200

        # 4. Put Object
        key = "documents/report.pdf"
        body = b"%PDF-1.4 Hello World PDF Content"
        put_res = self.s3_client.put_object(
            Bucket=bucket_name, Key=key, Body=body, ContentType="application/pdf"
        )
        assert put_res["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert "ETag" in put_res

        # 5. Get Object
        get_res = self.s3_client.get_object(Bucket=bucket_name, Key=key)
        downloaded = get_res["Body"].read()
        assert downloaded == body
        assert get_res["ContentType"] == "application/pdf"

        # 6. Range Download (bytes=0-4)
        range_res = self.s3_client.get_object(Bucket=bucket_name, Key=key, Range="bytes=0-4")
        assert range_res["Body"].read() == b"%PDF-"
        assert range_res["ResponseMetadata"]["HTTPStatusCode"] == 206

        # 7. Head Object
        head_o = self.s3_client.head_object(Bucket=bucket_name, Key=key)
        assert head_o["ContentLength"] == len(body)
        assert head_o["ResponseMetadata"]["HTTPStatusCode"] == 200

        # 8. List Objects V2
        list_v2 = self.s3_client.list_objects_v2(Bucket=bucket_name)
        assert list_v2["KeyCount"] == 1
        assert list_v2["Contents"][0]["Key"] == key

        # 9. Copy Object
        copy_key = "documents/report_backup.pdf"
        self.s3_client.copy_object(
            Bucket=bucket_name,
            Key=copy_key,
            CopySource={"Bucket": bucket_name, "Key": key},
        )
        copied_res = self.s3_client.get_object(Bucket=bucket_name, Key=copy_key)
        assert copied_res["Body"].read() == body

        # 10. Multipart Upload
        mp_key = "bigdata/chunk.bin"
        mp_init = self.s3_client.create_multipart_upload(Bucket=bucket_name, Key=mp_key)
        upload_id = mp_init["UploadId"]

        p1 = self.s3_client.upload_part(
            Bucket=bucket_name, Key=mp_key, UploadId=upload_id, PartNumber=1, Body=b"PART_1_"
        )
        p2 = self.s3_client.upload_part(
            Bucket=bucket_name, Key=mp_key, UploadId=upload_id, PartNumber=2, Body=b"PART_2_"
        )

        parts_list = self.s3_client.list_parts(Bucket=bucket_name, Key=mp_key, UploadId=upload_id)
        assert len(parts_list["Parts"]) == 2

        self.s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=mp_key,
            UploadId=upload_id,
            MultipartUpload={
                "Parts": [
                    {"ETag": p1["ETag"], "PartNumber": 1},
                    {"ETag": p2["ETag"], "PartNumber": 2},
                ]
            },
        )
        mp_res = self.s3_client.get_object(Bucket=bucket_name, Key=mp_key)
        assert mp_res["Body"].read() == b"PART_1_PART_2_"

        # 11. Presigned URL Generation
        presigned_url = self.s3_client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket_name, "Key": key}, ExpiresIn=300
        )
        http_res = requests.get(presigned_url)
        assert http_res.status_code == 200
        assert http_res.content == body

        # 12. S3 Error Code Compatibility (NoSuchKey)
        with pytest.raises(ClientError) as exc_info:
            self.s3_client.get_object(Bucket=bucket_name, Key="nonexistent.file")
        err_code = exc_info.value.response["Error"]["Code"]
        assert err_code == "NoSuchKey"

        # 13. Delete Objects & Bucket
        self.s3_client.delete_object(Bucket=bucket_name, Key=key)
        self.s3_client.delete_object(Bucket=bucket_name, Key=copy_key)
        self.s3_client.delete_object(Bucket=bucket_name, Key=mp_key)
        self.s3_client.delete_bucket(Bucket=bucket_name)
