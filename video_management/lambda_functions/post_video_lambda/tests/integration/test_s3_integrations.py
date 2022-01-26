from dataclasses import dataclass
from datetime import date
from os import environ
from os import path

import boto3
import pytest
import requests
from pytest_docker import docker_services
from requests.exceptions import ConnectionError
from urllib3.exceptions import ProtocolError


def is_responsive(url: str) -> bool:
    try:
        response = requests.get(url)
        if response.status_code == 404 and response.text == '{"status": "running"}':
            return True
        return False
    except (ConnectionError, ProtocolError):
        return False


@pytest.fixture(scope="session")
def docker_compose_file():
    dir = path.dirname(__file__)
    return path.join(dir, "docker-compose.yml")


@dataclass
class VarsForTesting:
    s3_bucket = "source"
    s3_key = "thistestvideo.mp4"
    client_id = 123
    client_secret = "monkey"  # pragma: allowlist secret
    username = "joker"
    password = "secretnolonger"  # pragma: allowlist secret
    wp_site_id = 14802075
    wp_category = "videos"
    post_name = "This Awesome video"
    login_called = False
    access_token = "testTokenResponse"
    video_date = date.today()
    aws_region = "us-east-2"
    wp_post_param_name = "/integration/test/param"
    wp_post_id = 123
    wp_post_url = "https://localhost/123"
    aws_endpoint = None


S3_POST_NOTIFICATION_EVENT = {
    "Records": [
        {
            "eventVersion": "2.0",
            "eventSource": "aws:s3",
            "awsRegion": VarsForTesting.aws_region,
            "eventTime": "1970-01-01T00:00:00.000Z",
            "eventName": "ObjectCreated:Put",
            "userIdentity": {"principalId": "EXAMPLE"},
            "requestParameters": {"sourceIPAddress": "127.0.0.1"},
            "responseElements": {
                "x-amz-request-id": "EXAMPLE123456789",
                "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH",
            },
            "s3": {
                "s3SchemaVersion": "1.0",
                "configurationId": "testConfigRule",
                "bucket": {
                    "name": VarsForTesting.s3_bucket,
                    "ownerIdentity": {"principalId": "EXAMPLE"},
                    "arn": f"arn:aws:s3:::{VarsForTesting.s3_bucket}",
                },
                "object": {
                    "key": VarsForTesting.s3_key,
                    "size": 1024,
                    "eTag": "0123456789abcdef0123456789abcdef",  # pragma: allowlist secret
                    "sequencer": "0A1B2C3D4E5F678901",  # pragma: allowlist secret
                },
            },
        }
    ]
}


class Response:
    """Class returned to wordpress loosely mocking a requests library response."""

    def __init__(
        self, json: dict = None, status_code: int = None, post_status: str = None
    ) -> None:
        self._json = json
        self.status_code = status_code
        self.post_status = post_status

    def json(self):
        return self._json


@pytest.fixture(scope="session")
def localstack_with_bucket(docker_services):
    """Setup localstack for testing.

    Creates a source S3 bucket, S3 object and SSM parameter to use.
    """
    # Start localstack
    environ["SERVICES"] = "s3"
    port = docker_services.port_for("localstack", 4566)
    VarsForTesting.aws_endpoint = f"http://localhost:{port}"
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=0.5,
        check=lambda: is_responsive(VarsForTesting.aws_endpoint),
    )

    # Create S3 bucket
    s3 = boto3.resource("s3", endpoint_url=VarsForTesting.aws_endpoint)
    s3.Bucket(VarsForTesting.s3_bucket).create()
    environ["SOURCE_BUCKET"] = VarsForTesting.s3_bucket

    # Create S3 object (file)
    tags = f"post_name={VarsForTesting.post_name}&video_date={VarsForTesting.video_date.isoformat()}"
    s3.meta.client.put_object(
        Body=b"test file",
        Bucket=environ["SOURCE_BUCKET"],
        Key=VarsForTesting.s3_key,
        Tagging=tags,
    )

    # Create SSM parameter
    environ["WPPOSTPARAM"] = VarsForTesting.wp_post_param_name
    ssm_client = boto3.client("ssm", endpoint_url=VarsForTesting.aws_endpoint)
    response = ssm_client.put_parameter(
        Name=VarsForTesting.wp_post_param_name,
        Value=f'{{"client_id":{VarsForTesting.client_id},"client_secret":"{VarsForTesting.client_secret}","username":"{VarsForTesting.username}", "password":"{VarsForTesting.password}","wp_site_id":{VarsForTesting.wp_site_id}, "post_category":"{VarsForTesting.wp_category}"}}',
        Type="SecureString",
        DataType="text",
    )
    environ["WPPOSTPARAM_VERSION"] = str(response["Version"])


class WPMock:
    """Test mock for the wordpress class."""

    def login(self, **kwargs):
        """Mock WordPress login call, here we only care that it was called."""
        assert not VarsForTesting.login_called
        VarsForTesting.login_called = True
        assert kwargs["client_id"] == VarsForTesting.client_id
        assert kwargs["client_secret"] == VarsForTesting.client_secret
        assert kwargs["username"] == VarsForTesting.username
        assert kwargs["password"] == VarsForTesting.password
        return VarsForTesting.access_token

    def post(self, **kwargs):
        """Mock WordPress post. Assert on and return the data from class init."""
        video_url = f"https://s3-{VarsForTesting.aws_region}.amazonaws.com/{VarsForTesting.s3_bucket}/{VarsForTesting.s3_key}"
        content = f"Sunday sermon\n{VarsForTesting.video_date.strftime('%B %d, %Y')}\n{video_url}"
        assert VarsForTesting.login_called
        assert kwargs["site_id"] == VarsForTesting.wp_site_id
        assert kwargs["title"] == VarsForTesting.post_name
        assert kwargs["content"] == content
        assert kwargs["category"] == VarsForTesting.wp_category
        return VarsForTesting.wp_post_id, VarsForTesting.wp_post_url


def test_integration(localstack_with_bucket, monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT", VarsForTesting.aws_endpoint)
    from lambda_function import lambda_handler

    monkeypatch.setattr("lambda_function.WP", WPMock)
    lambda_handler(S3_POST_NOTIFICATION_EVENT, "")
    s3 = boto3.resource("s3", endpoint_url=VarsForTesting.aws_endpoint)
    tagset = s3.meta.client.get_object_tagging(
        Bucket=VarsForTesting.s3_bucket, Key=VarsForTesting.s3_key
    )
    tag_dict = {}
    for x in tagset["TagSet"]:
        tag_dict[x["Key"]] = x["Value"]
    assert tag_dict["wp_site_id"] == f"{VarsForTesting.wp_site_id}"
    assert tag_dict["wp_post_id"] == f"{VarsForTesting.wp_post_id}"
    assert tag_dict["publish_date"] == date.today().isoformat()
    assert tag_dict["post_name"] == VarsForTesting.post_name
    assert tag_dict["video_date"] == VarsForTesting.video_date.isoformat()
