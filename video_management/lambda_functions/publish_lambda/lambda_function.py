import logging
from enum import Enum
from os import getenv
from sys import stdout
from uuid import uuid4

import boto3
from pydantic.dataclasses import dataclass


class ClamScanStatus(Enum):
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    UNKNOWN = "N/A"


class ClamScanSource(Enum):
    SERVERLESS_CLAMSCAN = "serverless-clamscan"


@dataclass
class ClamScanPayload:
    source: ClamScanSource
    input_bucket: str
    input_key: str
    status: ClamScanStatus
    message: str


@dataclass
class ClamScanNotificationEvent:
    version: str
    timestamp: str
    requestContext: object
    requestPayload: object
    responseContext: object
    responsePayload: ClamScanPayload


logging.basicConfig(
    level=getattr(logging, getenv("LOGGING", "WARN").upper(), logging.INFO)
)
logger = logging.getLogger("post_video")
logger.addHandler(logging.StreamHandler(stdout))


def load_event(event: dict) -> ClamScanPayload:
    scan_event = ClamScanNotificationEvent(**event)

    if scan_event.responsePayload.input_bucket != getenv("SOURCE_BUCKET"):
        raise ValueError("Unexpected bucket received")
    return scan_event.responsePayload


def lambda_handler(event: dict, context) -> None:
    logger.debug(f"Event: {event}")
    logger.debug(f"Context: {context}")

    scan_event = load_event(event)

    if scan_event.status == ClamScanStatus.CLEAN:
        PublishLambda().move_video_to_published(scan_event)
    elif scan_event.status == ClamScanStatus.INFECTED:
        PublishLambda().delete_file(scan_event)
    else:
        raise ValueError("Unknown ClamAV status: N/A")


class PublishLambda:
    def __init__(self):
        self.s3 = boto3.resource("s3", endpoint_url=getenv("AWS_ENDPOINT"))

    def delete_file(self, scan_event: ClamScanPayload) -> bool:
        delete_object = self.s3.Object(scan_event.input_bucket, scan_event.input_key)
        response = delete_object.delete()
        return response["ResponseMetadata"]["HTTPStatusCode"] == 204

    def copy_file(self, scan_event: ClamScanPayload, key: str) -> None:
        source_object_dict = {
            "Bucket": scan_event.input_bucket,
            "Key": scan_event.input_key,
        }
        self.s3.Object(getenv("DEST_BUCKET"), key).copy(source_object_dict)

    def copy_tags(self, scan_event: ClamScanPayload, key: str) -> None:
        tagset = self.s3.meta.client.get_object_tagging(
            Bucket=scan_event.input_bucket, Key=scan_event.input_key
        )["TagSet"]
        if len(tagset) != 0:
            self.s3.meta.client.put_object_tagging(
                Bucket=getenv("DEST_BUCKET"), Key=key, Tagging={"TagSet": tagset}
            )

    def move_video_to_published(self, scan_event: ClamScanPayload) -> bool:
        destination_key = self.get_unique_filename(scan_event.input_key)
        self.copy_file(scan_event, destination_key)
        logger.debug(f"Created new file: {destination_key}")
        self.copy_tags(scan_event, destination_key)
        if not self.delete_file(scan_event):
            logger.warn(f"Failed to delete file. {scan_event.input_key}")
            return False
        return True

    def get_unique_filename(self, proposed_filename: str) -> str:
        filename = f"{uuid4().hex}_{proposed_filename.replace(' ', '_')}"

        while filename in self.s3.meta.client.list_objects(
            Bucket=getenv("DEST_BUCKET")
        ):
            filename = f"{uuid4().hex}_{proposed_filename.replace(' ', '_')}"
        logger.debug(f"S3 Key to use for upload: {filename}")
        return filename
