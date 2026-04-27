"""
S3 Storage backends — Media ve Static ayrı prefix'lerle.
"""
from storages.backends.s3boto3 import S3Boto3Storage


class MediaS3Storage(S3Boto3Storage):
    """Media dosyaları (kıyafet görselleri vb.) — media/ prefix."""
    location = "media"


class StaticS3Storage(S3Boto3Storage):
    """Statik dosyalar (CSS/JS) — static/ prefix."""
    location = "static"
