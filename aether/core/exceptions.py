"""S3 Error Codes, Exception hierarchy, and XML Error Response Generator."""

import xml.etree.ElementTree as ET
from typing import Optional
from django.http import HttpResponse


class S3Error(Exception):
    """Base exception for all S3 API errors."""

    code: str = "InternalError"
    message: str = "We encountered an internal error. Please try again."
    status_code: int = 500

    def __init__(
        self,
        message: Optional[str] = None,
        resource: Optional[str] = None,
        request_id: str = "aether-req-0000",
    ):
        if message:
            self.message = message
        self.resource = resource or ""
        self.request_id = request_id
        super().__init__(self.message)

    def to_xml(self) -> str:
        root = ET.Element("Error")
        ET.SubElement(root, "Code").text = self.code
        ET.SubElement(root, "Message").text = self.message
        ET.SubElement(root, "Resource").text = self.resource
        ET.SubElement(root, "RequestId").text = self.request_id
        ET.SubElement(root, "HostId").text = "aether-storage-node"
        xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
        return xml_str

    def to_response(self) -> HttpResponse:
        return HttpResponse(
            self.to_xml(),
            status=self.status_code,
            content_type="application/xml",
        )


class NoSuchBucketError(S3Error):
    code = "NoSuchBucket"
    message = "The specified bucket does not exist."
    status_code = 404


class NoSuchKeyError(S3Error):
    code = "NoSuchKey"
    message = "The specified key does not exist."
    status_code = 404


class BucketAlreadyExistsError(S3Error):
    code = "BucketAlreadyExists"
    message = "The requested bucket name already exists."
    status_code = 409


class BucketNotEmptyError(S3Error):
    code = "BucketNotEmpty"
    message = "The bucket you tried to delete is not empty."
    status_code = 409


class AccessDeniedError(S3Error):
    code = "AccessDenied"
    message = "Access Denied"
    status_code = 403


class SignatureDoesNotMatchError(S3Error):
    code = "SignatureDoesNotMatch"
    message = "The request signature we calculated does not match the signature you provided."
    status_code = 403


class InvalidDigestError(S3Error):
    code = "InvalidDigest"
    message = "The Content-MD5 or checksum you specified did not match what we received."
    status_code = 400


class EntityTooLargeError(S3Error):
    code = "EntityTooLarge"
    message = "Your proposed upload exceeds the maximum allowed object size."
    status_code = 400


class NoSuchUploadError(S3Error):
    code = "NoSuchUpload"
    message = "The specified multipart upload does not exist."
    status_code = 404


class InvalidRangeError(S3Error):
    code = "InvalidRange"
    message = "The requested range cannot be satisfied."
    status_code = 416


class PreconditionFailedError(S3Error):
    code = "PreconditionFailed"
    message = "At least one of the preconditions you specified did not hold."
    status_code = 412


class InvalidBucketNameError(S3Error):
    code = "InvalidBucketName"
    message = "The specified bucket is not valid."
    status_code = 400


class QuotaExceededError(S3Error):
    code = "QuotaExceeded"
    message = "Storage quota for bucket or user has been exceeded."
    status_code = 400


class ObjectLockedError(S3Error):
    code = "ObjectLocked"
    message = "Object is locked under Governance or Compliance retention rules."
    status_code = 403
