import datetime

import pytest
from botocore.stub import Stubber
from lambda_function import add_tags
from lambda_function import get_ssm_parameter
from lambda_function import get_tags
from lambda_function import s3_resource
from lambda_function import ssm_client
from lambda_function import wp_post_video

from models import S3Bucket
from models import S3Object
from models import S3Type
from models import VideoMetadata
from models import WPPostParam


class WPMock:
    """Test mock for the wordpress class."""

    def __init__(
        self,
        post_id: int,
        post_url: str,
        site_id: int,
        post_title: str,
        in_post_content: str,
    ):
        """Create class, intake data to return and assert on in the mock."""
        self.login_called = False
        self.post_id = post_id
        self.post_url = post_url
        self._site_id = site_id
        self._post_title = post_title
        self._in_post_content = in_post_content

    def login(self, **kwargs):
        """Mock WordPress login call, here we only care that it was called."""
        self.login_called = True

    def post(self, **kwargs):
        """Mock WordPress post. Assert on and return the data from class init."""
        assert kwargs["site_id"] == self._site_id
        assert self._in_post_content in kwargs["content"]
        assert kwargs["title"] == self._post_title
        return self.post_id, self.post_url


def test_get_ssm_parameter():
    """Validates that an expected AWS parameter will match the expected data model."""
    param_name = "thisone"
    param_version = 1
    ssm_stub = Stubber(ssm_client)
    ssm_stub.add_response(
        "get_parameter",
        expected_params={
            "Name": f"{param_name}:{param_version}",
            "WithDecryption": True,
        },
        # Note to future self. Supplying a partial response like this will cause
        # validation failures in the AWS libraries when the stub is not active.
        service_response={
            "Parameter": {
                "Value": '{"client_id": 123,"client_secret": "exampleSecret","username": "awesome_dev_account","password": "exampleSuperSecret","wp_site_id": 321,"post_category": "tag1"}',
            }
        },
    )
    with ssm_stub:
        response = get_ssm_parameter(f"{param_name}:{param_version}")
    assert isinstance(response, WPPostParam)
    ssm_stub.assert_no_pending_responses()


def test_get_tags():
    """Validates expected tags on a video at runtime will load into model."""
    bucket = "specialBucket"
    key = "publicVideo"
    s3_stub = Stubber(s3_resource.meta.client)
    s3_stub.add_response(
        "get_object_tagging",
        expected_params={"Bucket": bucket, "Key": key},
        service_response={
            "VersionId": "string",
            "TagSet": [
                {"Key": "post_name", "Value": "title"},
                {"Key": "video_date", "Value": f"{datetime.date.today().isoformat()}"},
            ],
        },
    )
    s3_type = S3Type(
        **{
            "s3SchemaVersion": "1.0",
            "configurationId": "testConfigRule",
            "bucket": {
                "name": bucket,
                "ownerIdentity": {"principalId": "EXAMPLE"},
                "arn": "arn:aws:s3:::example-bucket",
            },
            "object": {
                "key": key,
                "size": 1024,
                "eTag": "0123456789abcdef0123456789abcdef",  # pragma: allowlist secret
                "sequencer": "0A1B2C3D4E5F678901",  # pragma: allowlist secret
            },
        }
    )
    with s3_stub:
        response = get_tags(s3_type)
    assert type(response) == VideoMetadata
    assert response.post_name == "title"
    assert response.publish_date is None
    assert response.wp_site_id is None
    assert response.wp_post_id is None
    s3_stub.assert_no_pending_responses()


def test_add_tags():
    """Validate that code attempts to add tags to a S3 video."""
    bucket = "specialBucket"
    key = "publicVideo"
    tagset = {
        "TagSet": [
            {"Key": "post_name", "Value": "title"},
            {"Key": "video_date", "Value": f"{datetime.date.today().isoformat()}"},
            {"Key": "publish_date", "Value": datetime.date.today().isoformat()},
            {"Key": "wp_site_id", "Value": "123"},
            {"Key": "wp_post_id", "Value": "987"},
        ]
    }
    s3_stub = Stubber(s3_resource.meta.client)
    s3_stub.add_response(
        "get_object_tagging",
        expected_params={"Bucket": bucket, "Key": key},
        service_response={
            "VersionId": "1",
            "TagSet": [
                {"Key": "post_name", "Value": "title"},
                {"Key": "video_date", "Value": f"{datetime.date.today().isoformat()}"},
            ],
        },
    )
    s3_stub.add_response(
        "put_object_tagging",
        expected_params={"Bucket": bucket, "Key": key, "Tagging": tagset},
        service_response={"VersionId": "1"},
    )
    s3_type = S3Type(
        **{
            "bucket": {"name": bucket},
            "object": {"key": key},
        }
    )
    with s3_stub:
        add_tags(s3_type, 123, 987)
    s3_stub.assert_no_pending_responses()


def test_post_video(monkeypatch):
    """Validate that all the calls necessary to post a video were called.

    This is more integration and testing flow than every call."""
    # Arrange
    # **Env variables
    monkeypatch.setenv("WPPOSTPARAM", "/this/param")
    monkeypatch.setenv("WPPOSTPARAM_VERSION", "42")
    # **Parameter Store mock
    ssm_stub = Stubber(ssm_client)
    ssm_stub.add_response(
        "get_parameter",
        service_response={
            "Parameter": {
                "Value": '{"client_id": 123,"client_secret": "exampleSecret","username": "awesome_dev_account","password": "exampleSuperSecret","wp_site_id": 321,"post_category": "tag1"}',
            }
        },
    )
    # **S3 mock
    s3_stub = Stubber(s3_resource.meta.client)
    s3_stub.add_response(
        "get_bucket_location", service_response={"LocationConstraint": "us-east-2"}
    )
    s3_stub.add_response(
        "get_object_tagging",
        service_response={
            "VersionId": "1",
            "TagSet": [
                {"Key": "post_name", "Value": "title"},
                {"Key": "video_date", "Value": f"{datetime.date.today().isoformat()}"},
            ],
        },
    )
    s3_stub.add_response(
        "get_object_tagging",
        service_response={
            "VersionId": "1",
            "TagSet": [
                {"Key": "post_name", "Value": "title"},
                {"Key": "video_date", "Value": f"{datetime.date.today().isoformat()}"},
            ],
        },
    )
    s3_stub.add_response(
        "put_object_tagging",
        service_response={
            "VersionId": "1",
        },
    )
    # **WordPress class mock
    wp_mock = WPMock(
        post_id=693,
        post_url="https://localhost:693",
        site_id=321,
        post_title="title",
        in_post_content="https://s3-us-east-2.amazonaws.com/MyBucket/ThisVideo",
    )
    monkeypatch.setattr("lambda_function.WP.login", wp_mock.login)
    monkeypatch.setattr("lambda_function.WP.post", wp_mock.post)
    # **S3 test object
    s3 = S3Type(
        bucket=S3Bucket(name="MyBucket"),
        object=S3Object(key="ThisVideo", versionId="1"),
    )
    # Act
    with ssm_stub:
        with s3_stub:
            post_id = wp_post_video(s3)
    # Assert
    assert post_id == wp_mock.post_id
    ssm_stub.assert_no_pending_responses()
    s3_stub.assert_no_pending_responses()
