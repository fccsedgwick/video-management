from json import loads
from os import getenv
from uuid import uuid4

import boto3
from jsonschema import validate

SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "serverless-clamscan-output",
    "description": "successful clamscan output: https://github.com/awslabs/cdk-serverless-clamscan/blob/main/API.md",
    "type": "object",
    "properties": {
        "source": {
            "description": "Source of the event",
            "type": "string",
            "enum": ["serverless-clamscan"],
        },
        "input_bucket": {
            "description": "S3 bucket holding the scanned object",
            "type": "string",
        },
        "input_key": {"description": "object that was scanned", "type": "string"},
        "status": {
            "description": "scan output",
            "type": "string",
            "enum": ["CLEAN", "INFECTED", "N/A"],
        },
        "message": {"description": "clamav message - not used", "type": "string"},
    },
    "required": ["source", "input_bucket", "input_key", "status", "message"],
}


def lambda_handler(event: str, context) -> None:
    """Main Lambda handler.

    Args:
        event ([type]): event object that fired the lambda (from API GW) context
                        ([type]): additional context for the lambda passed in by AWS

    Returns:
        OembedResponse: oEmbed response in either json or xml format as requested by
                        the consumer
    """
    print("## Event")
    print(event)

    print("## Context")
    print(context)

    validate(event, SCHEMA)

    av_event = loads(event)

    if av_event["input_bucket"] != getenv("SOURCE_BUCKET"):
        raise ValueError("Unexpected bucket received")

    s3 = boto3.resource("s3")
    source_object = s3.Object(getenv("SOURCE_BUCKET"), av_event["input_key"])

    if av_event["status"] == "CLEAN":
        move_video_to_published(s3, av_event["input_key"])
    elif av_event["status"] == "INFECTED":
        delete_file(source_object)
    else:
        print("Unknown ClamAV status: N/A")


def delete_file(object) -> bool:
    response = object.delete()
    if response["ResponseMetadata"]["HTTPStatusCode"] == 204:
        print(f"file deleted: {str(object)}")
        return True
    else:
        print(f"Failed to deleted: {str(object)}")
        return False


def move_video_to_published(s3: boto3.session.Session.resource, key) -> bool:
    destination_object = get_destination_object(s3, key)
    source_object = s3.Object(getenv("SOURCE_BUCKET"), key)
    response = destination_object.copy_from(source_object)
    if response["ResponseMetadata"]["HTTPStatusCode"] == 204:
        print(f"New file created: {str(destination_object)}")
        return delete_file(source_object)
    else:
        print(f"Failed to create new file. Leaving {str(source_object)}")
        return False


def get_destination_object(s3: boto3.session.Session.resource, key):
    return s3.Object(getenv("DEST_BUCKET"), get_unique_filename(key))


def get_unique_filename(proposed_filename: str) -> str:
    filename = f"{uuid4().hex}_{proposed_filename.replace(' ', '_')}"

    client = boto3.client("s3")
    while filename in client.list_objects(Bucket=getenv("DEST_BUCKET")):
        filename = f"{uuid4().hex}_{proposed_filename.replace(' ', '_')}"
    print(f"S3 Key to use for upload: {filename}")
    return filename
