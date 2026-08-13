"""Celery Background Tasks for S3 Lifecycle and Expiration Cleanup."""

import logging
from datetime import datetime, timedelta, timezone
from celery import shared_task

from aether.apps.lifecycle.models import LifecycleRule
from aether.apps.multipart.models import MultipartUpload
from aether.apps.multipart.services import MultipartService
from aether.apps.objects.models import Object
from aether.apps.objects.services import ObjectService

logger = logging.getLogger(__name__)


@shared_task
def process_lifecycle_rules():
    """Celery background job running periodically to execute S3 lifecycle rules."""
    logger.info("Executing periodic S3 lifecycle rules task...")
    now = datetime.now(timezone.utc)
    rules = LifecycleRule.objects.filter(status="Enabled")

    deleted_count = 0
    for rule in rules:
        if rule.expiration_days:
            cutoff = now - timedelta(days=rule.expiration_days)
            expired_objects = Object.objects.filter(
                bucket=rule.bucket,
                key__startswith=rule.prefix,
                last_modified__lt=cutoff,
                is_latest=True,
            )
            for obj in expired_objects:
                ObjectService.delete_object(rule.bucket.name, obj.key)
                deleted_count += 1

    logger.info(f"Lifecycle rule task finished. Expired objects removed: {deleted_count}")
    return deleted_count


@shared_task
def cleanup_expired_multipart_uploads(days: int = 7):
    """Celery background task cleaning up abandoned incomplete multipart uploads."""
    logger.info(f"Cleaning up incomplete multipart uploads older than {days} days...")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    abandoned = MultipartUpload.objects.filter(status="IN_PROGRESS", created_at__lt=cutoff)

    aborted_count = 0
    for upload in abandoned:
        try:
            MultipartService.abort_multipart_upload(upload.bucket.name, upload.upload_id)
            aborted_count += 1
        except Exception as e:
            logger.error(f"Failed aborting upload {upload.upload_id}: {e}")

    logger.info(f"Multipart cleanup completed. Aborted uploads: {aborted_count}")
    return aborted_count
