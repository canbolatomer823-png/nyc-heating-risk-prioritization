"""Sample Lambda function for ingesting public API data into S3.

The goal is to demonstrate a minimalist, testable structure. Replace SOURCE_URL
with your dataset endpoint or pre-signed download link.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

import boto3
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET_NAME = os.environ["DATA_LAKE_BUCKET"]
SOURCE_URL = os.environ.get("SOURCE_URL", "https://api.publicapis.org/random")


def fetch_payload() -> Dict[str, Any]:
    """Fetches data from the external API with basic error handling."""
    response = requests.get(SOURCE_URL, timeout=15)
    response.raise_for_status()
    return response.json()


def upload_to_s3(payload: Dict[str, Any]) -> str:
    """Serializes the payload to S3 under the raw/ prefix."""
    key = f"raw/ingest_date={datetime.utcnow():%Y-%m-%d}/payload-{datetime.utcnow():%H%M%S}.json"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(payload).encode("utf-8"),
        ContentType="application/json",
    )
    return key


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry point."""
    logger.info("event=%s", event)
    payload = fetch_payload()
    key = upload_to_s3(payload)
    logger.info("uploaded key=%s", key)
    return {"status": "ok", "s3_key": key}


if __name__ == "__main__":
    example = fetch_payload()
    print(upload_to_s3(example))
