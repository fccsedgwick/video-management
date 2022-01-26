import json
import logging
from datetime import date
from os import getenv
from sys import stdout
from typing import Optional

import boto3
from wordpress import WP

from models import S3NotificationEvent
from models import S3Type
from models import VideoMetadata
from models import WPPostParam


logging.basicConfig(
    level=getattr(logging, getenv("LOGGING", "INFO").upper(), logging.INFO)
)
logger = logging.getLogger("post_video")
logger.addHandler(logging.StreamHandler(stdout))

s3_resource = boto3.resource("s3", endpoint_url=getenv("AWS_ENDPOINT"))
ssm_client = boto3.client("ssm", endpoint_url=getenv("AWS_ENDPOINT"))


def load_events(event: dict) -> list[S3NotificationEvent]:
    """Parse AWS event into data models we need.

    Extracts the relevant information about the S3 Put event notification
    that triggered the notification. Performs some filtering to ensure that
    we are acting in the current region, which is expected by the current
    architecture. Additional data formatting and mild validation  is performed
    by the data models.

    Args:
        event (dict): json document that contains data for the lambda function to
                      process.

    Returns:
        list[S3NotificationEvent]: list of events (in dataclasses) which describe
                                   the put event(s). It is expected that there will
                                   be only one event in our usage, but accomodating
                                   for multiples.
    """
    events = []
    for event in event["Records"]:
        s3_event = S3NotificationEvent(**event)
        if s3_event.eventName != "ObjectCreated:Put":
            continue
        if s3_event.awsRegion != getenv("AWS_REGION"):
            continue
        events.append(s3_event)
    return events


def lambda_handler(event: dict, context) -> None:
    """Entry point called by Lambda.

    See AWS[Lambda documentation](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html)
    for more details.

    Args:
        event (dict): The event which triggers this lambda
        context (dict): Additional context supplied by AWS
    """
    logger.debug(f"Event: {event}")
    logger.debug(f"Context: {context}")

    s3_events = load_events(event)
    logger.info(f"Found {len(s3_events)} S3 Put object event(s)")
    for s3_event in s3_events:
        wp_post_video(s3_event.s3)


def get_tags(s3_object: S3Type) -> VideoMetadata:
    """Get tags we need from a published video.

    Args:
        s3_object (S3Type): S3 object metadata triggering the notification.
                            Reference :class: `models.S3Type`

    Returns:
        VideoMetadata: datamodel describing the tags. Reference :class:
                       `models.VideoMetadata`.
    """
    tagset = s3_resource.meta.client.get_object_tagging(
        Bucket=s3_object.bucket.name, Key=s3_object.object.key
    )
    logger.debug(f"get_tags:get_object_tagging: {tagset}")
    tag_dict = {}
    for x in tagset["TagSet"]:
        tag_dict[x["Key"]] = x["Value"]
    return VideoMetadata(**tag_dict)


# OperationAbortedError
def add_tags(
    s3_object: S3Type,
    wp_site_id: int,
    wp_post_id: int,
    publish_date: date = date.today(),
) -> Optional[int]:
    """Add metadata about the WordPress post to the published S3 video file.

    Args:
        s3_object (S3Type): Information describing the S3 object to update
        wp_site_id (int): The WordPress Site ID to which the video was posted
        wp_post_id (int): The ID of the post on the WordPress site
        publish_date (str, optional): isoformat of the date on which the video was
                                      posted. Defaults to datetime.now().isoformat().
                                      AWS restrictions require string fields for all
                                      tag keys and values.
    """
    current_tags = get_tags(s3_object)
    current_tags.publish_date = publish_date
    current_tags.wp_site_id = wp_site_id
    current_tags.wp_post_id = wp_post_id
    tagset = {"TagSet": current_tags.as_tags()}
    response = s3_resource.meta.client.put_object_tagging(
        Bucket=s3_object.bucket.name, Key=s3_object.object.key, Tagging=tagset
    )
    logger.debug(f"add_tags.put_object_tagging: {response}")
    if "VersionId" in response.keys():
        return response["VersionId"]
    return None


def get_ssm_parameter(param_name: str) -> WPPostParam:
    """Retrieve information required to post to the WordPress site.

    Args:
        param_name (str): Name of the SecureString Parameter in AWS

    Returns:
        WPPostParam: Data model describing the required data. Ref: `models.WPPostParam`
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm.html#SSM.Client.get_parameter
    param_value = ssm_client.get_parameter(Name=param_name, WithDecryption=True)[
        "Parameter"
    ]["Value"]
    wp_info = WPPostParam(**json.loads(param_value))
    return wp_info


def wp_post_video(s3_object: S3Type) -> int:
    """Create a post on the WordPress site, publishing the video.

    Args:
        s3_object (S3Type): Information describing the video to post

    Returns:
        int: The ID of the created post on the WordPress site
    """
    param_name = f"{getenv('WPPOSTPARAM')}:{getenv('WPPOSTPARAM_VERSION')}"
    logger.debug(f"WPPostParmeter: {param_name}")
    wp_info = get_ssm_parameter(param_name)
    logger.debug(f"Retrieved information for WP Site: {wp_info.wp_site_id}")
    wp = WP()
    wp.login(
        client_id=wp_info.client_id,
        client_secret=wp_info.client_secret,
        username=wp_info.username,
        password=wp_info.password,
    )
    logger.debug("Logged into WP Site")

    s3_loc = s3_resource.meta.client.get_bucket_location(Bucket=s3_object.bucket.name)[
        "LocationConstraint"
    ]
    tags = get_tags(s3_object)
    url = f"https://s3-{s3_loc}.amazonaws.com/{s3_object.bucket.name}/{s3_object.object.key}"

    post_id, post_url = wp.post(
        site_id=wp_info.wp_site_id,
        title=tags.post_name,
        content=f"Sunday sermon\n{tags.video_date.strftime('%B %d, %Y')}\n{url}",
        category=wp_info.post_category,
    )
    logger.info(f"Video posted to site: {post_url}")

    if add_tags(s3_object, wp_info.wp_site_id, post_id) is None:
        logger.error("Failed to add tags")
    else:
        logger.info("Tags addes to S3 object")

    return post_id
