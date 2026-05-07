from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def s3_client(region_name: Optional[str] = None):
    return boto3.client("s3", region_name=region_name or os.getenv("AWS_REGION"))


def derive_s3_key(prefix: str, relative_key: str) -> str:
    clean_prefix = prefix.strip("/")
    clean_relative = relative_key.strip("/")
    if not clean_prefix:
        return clean_relative
    return f"{clean_prefix}/{clean_relative}"


def download_s3_object(bucket: str, key: str, destination: Path, region_name: Optional[str] = None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    s3_client(region_name=region_name).download_file(bucket, key, str(destination))
    return destination


def head_s3_object(bucket: str, key: str, region_name: Optional[str] = None) -> dict | None:
    try:
        return s3_client(region_name=region_name).head_object(Bucket=bucket, Key=key)
    except (ClientError, BotoCoreError):
        return None


def upload_file(local_path: Path, bucket: str, key: str, region_name: Optional[str] = None) -> dict:
    if not local_path.exists():
        raise FileNotFoundError(f"Missing local artifact: {local_path}")
    extra_args = {}
    content_type, _ = mimetypes.guess_type(str(local_path))
    if content_type:
        extra_args["ContentType"] = content_type
    s3 = s3_client(region_name=region_name)
    s3.upload_file(str(local_path), bucket, key, ExtraArgs=extra_args or None)
    return {
        "bucket": bucket,
        "key": key,
        "local_path": str(local_path),
        "content_type": content_type or "application/octet-stream",
    }
