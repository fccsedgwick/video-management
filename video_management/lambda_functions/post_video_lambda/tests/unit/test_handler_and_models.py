from copy import deepcopy
from os import environ

import pytest
from lambda_function import lambda_handler
from lambda_function import load_events

from models import S3Bucket
from models import S3NotificationEvent
from models import S3Object
from models import S3Type

S3_POST_NOTIFICATION_EVENT = {
    "Records": [
        {
            "eventVersion": "2.0",
            "eventSource": "aws:s3",
            "awsRegion": "us-east-2",
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
                    "name": "example-bucket",
                    "ownerIdentity": {"principalId": "EXAMPLE"},
                    "arn": "arn:aws:s3:::example-bucket",
                },
                "object": {
                    "key": "test%2Fkey",
                    "size": 1024,
                    "eTag": "0123456789abcdef0123456789abcdef",  # pragma: allowlist secret
                    "sequencer": "0A1B2C3D4E5F678901",  # pragma: allowlist secret
                },
            },
        }
    ]
}


def test_load_events():
    """Verify an S3 Put Object event will load correctly to models."""
    environ["AWS_REGION"] = "us-east-2"
    events = load_events(S3_POST_NOTIFICATION_EVENT)
    assert len(events) == 1
    assert isinstance(events[0], S3NotificationEvent)
    assert isinstance(events[0].s3, S3Type)
    assert isinstance(events[0].s3.bucket, S3Bucket)
    assert isinstance(events[0].s3.object, S3Object)


def test_region_validation(monkeypatch):
    """Verify events forwarded on into function are from the expected region."""
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    events = load_events(S3_POST_NOTIFICATION_EVENT)
    assert len(events) == 0


other_s3_notification_types = [
    "ObjectCreated:Post",
    "ObjectCreated:Copy",
    "ObjectCreated:CompleteMultipartUpload",
    "ObjectRemoved:Delete",
    "ObjectRemoved:DeleteMarkerCreated",
    "TestEvent",
]


@pytest.mark.parametrize("notification_type", other_s3_notification_types)
def test_s3_put_object_notification_validation(monkeypatch, notification_type):
    """Validate expectations out of pydantic data models used for the S3 event."""
    diff_region_event = deepcopy(S3_POST_NOTIFICATION_EVENT)
    diff_region_event["Records"][0]["eventName"] = notification_type
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    # Validate this event loads correctly then make sure its not returned
    S3NotificationEvent(**diff_region_event["Records"][0])
    events = load_events(diff_region_event)
    assert len(events) == 0


def test_handler(monkeypatch):
    """Validate the handler passes on expected information from a standard event."""
    call_count = 0

    def _mock_post_call(s3_object):
        nonlocal call_count
        call_count += 1
        assert isinstance(s3_object, S3Type)

    monkeypatch.setenv("AWS_REGION", "us-east-2")
    monkeypatch.setattr("lambda_function.wp_post_video", _mock_post_call)
    lambda_handler(S3_POST_NOTIFICATION_EVENT, "")
    assert call_count == 1
