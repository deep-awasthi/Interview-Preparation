"""URL Routing for S3 REST API Endpoints."""

from django.urls import path
from aether.apps.buckets.views import S3BucketRootView, S3BucketView
from aether.apps.objects.views import S3ObjectView

urlpatterns = [
    # List All Buckets
    path("", S3BucketRootView.as_view(), name="s3-root"),
    # Bucket Level Operations (Create Bucket, Delete Bucket, Head Bucket, List Objects)
    path("<str:bucket_name>", S3BucketView.as_view(), name="s3-bucket"),
    # Object Level Operations (Upload, Download, Delete, Head, Copy, Multipart Uploads)
    path("<str:bucket_name>/<path:object_key>", S3ObjectView.as_view(), name="s3-object"),
]
