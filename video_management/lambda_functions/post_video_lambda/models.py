from datetime import date
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import Extra
from pydantic import validator
from pydantic.dataclasses import dataclass


class S3Object(BaseModel, extra=Extra.allow):
    """S3 notification event object metadata.

    Data as sent from an S3 Notification event. This is the portion of the
    Record[n]["s3"]["object"] section of the event that we actually need. See
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html

    Attributes:
        key (str): S3 object-key
        versionId (int): object version if bucket is versioning-enabled, otherwise null
    """

    key: str
    versionId: Optional[str] = None


class S3Bucket(BaseModel, extra=Extra.allow):
    """S3 notification event bucket metadata.

    Data as sent from an S3 Notification event. This is the portion of the
    Record[n]["s3"]["bucket"] section of the event that we actually need. See
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html

    Attributes:
        name (str): bucket name
        arn: (str): bucket arn
    """

    name: str


class S3Type(BaseModel, extra=Extra.allow):
    """S3 notification event metadata.

    Data as sent from an S3 Notification event. This is the portion of the
    Record[n]["s3"] section of the event that we actually need. See
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html

    Attributes:
        bucket (S3Bucket): S3 bucket metadata
        object (S3Object): S3 object metadata
    """

    bucket: S3Bucket
    object: S3Object


class S3NotificationEvent(BaseModel, extra=Extra.allow):
    """S3 Notification Event.

    Data as sent from an S3 Notification event. This is the portion of the Records
    section of the event that we actually need. See
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html

    Attributes:
        awsRegion (str):
        eventName (str): The S3 event that occured (e.g. 'ObjectCreated:Put')
        s3 (S3Type): S3 bucket/object metadata used
    """

    awsRegion: str
    eventName: str
    s3: S3Type


@dataclass
class WPPostParam:
    """The credentialling information needed for the post.

    Attributes:
        client_id (int): WordPress application OAauth2 client id
        client_secret (str): WordPress application OAuth2 client secret
        username (str): WordPress developer account username
        password (str): WordPress developer account password
        wp_site_id (int): WordPress site to post the video
        post_category (str): Category to apply to the post
    """

    client_id: int
    client_secret: str
    username: str
    password: str
    wp_site_id: int
    post_category: str


class VideoMetadata(BaseModel, extra=Extra.allow):
    """Tags applied to a video file on S3.

    Attributes:
        post_name (str): The title that should be used for the WordPress post
        video_date (date): The date the video was taken. Isoformatted date will
                           be converted to date
        publish_date (Optional[date]): The date the post was made to WordPress.
                                       Isoformat string is converted to date
        wp_site_id (Optional[int]): The WordPress Site ID the post was made
        wp_post_id (Optional[int]): The ID of the WordPress post
    """

    post_name: str
    video_date: date
    publish_date: Optional[date] = None
    wp_site_id: Optional[int] = None
    wp_post_id: Optional[int] = None

    @classmethod
    def _validate_date(cls, date_to_validate):
        """Convert strings to dates. Assume the string is in isoformat.

        AWS limitations to storing strings in key/value pairs for tags.
        """
        if type(date_to_validate) == str:
            return date.fromisoformat(date_to_validate)
        elif type(date_to_validate) == datetime:
            return date(date_to_validate)
        return date_to_validate

    @validator("video_date")
    def _validate_video_dates(cls, v):
        return cls._validate_date(v)

    @validator("publish_date")
    def _validate_publish_date(cls, v):
        if v is None:
            return None
        return cls._validate_date(v)

    def as_tags(self) -> list[dict]:
        """Return attributes/values as a list for use in a TagSet for boto3 tagging."""
        tags = []
        non_null_tags = [x for x in self if x[1] is not None]
        for key, value in non_null_tags:
            if type(value) == date:
                value = f"{value.isoformat()}"
            tags.append({"Key": key, "Value": f"{value}"})
        return tags
