"""
Ingestion consumer for GTFS-like bus events.

Run locally with sample data:
python consumer.py --events ../data/sample_bus_events.json --s3-bucket YOUR_BUCKET --dry-run

In production, run inside EKS as a Deployment that reads from Kinesis/MSK
and writes validated payloads to S3 under raw/.
"""

import argparse
import json
import logging
import os
from datetime import datetime
from typing import Iterable, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ValidationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class BusEvent(BaseModel):
    trip_id: str
    route_id: str
    stop_id: str
    timestamp: int
    latitude: float
    longitude: float
    delay_seconds: int
    scheduled_arrival_ts: int


def load_events(path: str) -> List[BusEvent]:
    """Load and validate events from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return _validate_events(raw)


def _validate_events(raw_events) -> List[BusEvent]:
    events = []
    for item in raw_events:
        try:
            events.append(BusEvent(**item))
        except ValidationError as ve:
            logger.warning("skipping invalid event: %s", ve)
    return events


def load_from_kinesis(stream_name: str, limit: int, region: Optional[str]) -> List[BusEvent]:
    """Read a handful of records from Kinesis and validate them."""
    client = boto3.client("kinesis", region_name=region)
    desc = client.describe_stream(StreamName=stream_name)
    shard_id = desc["StreamDescription"]["Shards"][0]["ShardId"]
    iterator = client.get_shard_iterator(
        StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
    )["ShardIterator"]

    collected = []
    while iterator and len(collected) < limit:
        resp = client.get_records(ShardIterator=iterator, Limit=min(100, limit - len(collected)))
        iterator = resp.get("NextShardIterator")
        if not resp.get("Records"):
            break
        for record in resp["Records"]:
            try:
                payload = json.loads(record["Data"])
                collected.append(payload)
            except json.JSONDecodeError:
                logger.warning("skipping non-JSON record")
    return _validate_events(collected)


def upload_event(s3_client, bucket: str, event: BusEvent) -> str:
    """Serialize one event to S3 under the raw/ prefix."""
    key = f"raw/ingest_date={datetime.utcnow():%Y-%m-%d}/event-{event.trip_id}-{event.timestamp}.json"
    body = event.json().encode("utf-8")
    s3_client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
    return key


def process_events(events: Iterable[BusEvent], bucket: str, dry_run: bool = False) -> None:
    s3_client = boto3.client("s3", region_name=os.environ.get("AWS_REGION"))
    for event in events:
        if dry_run:
            logger.info("validated event (dry-run): route=%s stop=%s delay=%s", event.route_id, event.stop_id, event.delay_seconds)
            continue
        try:
            key = upload_event(s3_client, bucket, event)
            logger.info("uploaded to s3://%s/%s", bucket, key)
        except (ClientError, BotoCoreError) as e:
            logger.error("failed to upload event %s: %s", event.trip_id, e)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transit delay ingestion consumer")
    parser.add_argument("--events", help="Path to JSON array of events")
    parser.add_argument("--kinesis-stream", help="Kinesis stream name to consume from", default=os.environ.get("KINESIS_STREAM"))
    parser.add_argument("--kinesis-limit", type=int, default=200, help="Max records to read per run")
    parser.add_argument("--s3-bucket", help="Target S3 bucket for raw events", default=os.environ.get("RAW_BUCKET"))
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to S3")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.s3_bucket:
        raise SystemExit("Provide --s3-bucket or set RAW_BUCKET")

    if args.kinesis_stream:
        events = load_from_kinesis(args.kinesis_stream, args.kinesis_limit, os.environ.get("AWS_REGION"))
    elif args.events:
        events = load_events(args.events)
    else:
        raise SystemExit("Provide --events for local testing or --kinesis-stream in-cluster")

    logger.info("loaded %d events", len(events))
    process_events(events, args.s3_bucket, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
