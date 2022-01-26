from copy import deepcopy
from dataclasses import dataclass

import pytest
from wordpress import PostStatus
from wordpress import WP


def test_login_success(monkeypatch):
    """Test happy path Login."""
    login_called = False
    login_args = {
        "client_id": "id",
        "client_secret": "secret",  # pragma: allowlist secret
        "username": "user",
        "password": "pass",  # pragma: allowlist secret
    }
    wp_called_args = deepcopy(login_args)
    wp_called_args["grant_type"] = "password"

    def _mock_post(url, data):
        nonlocal login_called
        login_called = True
        assert url == "https://public-api.wordpress.com/oauth2/token"
        assert data == wp_called_args

        class Response:
            status_code = 200

            def json():
                return {
                    "access_token": "testTokenResponse",
                    "blog_id": "blogID",
                    "blog_url": "blogurl",
                    "token_type": "bearer",
                }

        return Response

    monkeypatch.setattr("requests.post", _mock_post)
    wp = WP()
    wp.login(**login_args)
    assert login_called
    assert wp._header["Authorization"] == "Bearer testTokenResponse"


def test_login_fail(monkeypatch):
    def _mock_post(url, data):
        class Response:
            status_code = 400

            def json():
                return {
                    "error": "invalid_client",
                    "error_description": "Unknown client_id",
                }

        return Response

    monkeypatch.setattr("requests.post", _mock_post)
    wp = WP()
    with pytest.raises(PermissionError):
        wp.login("id", "secret", "user", "pass")


def test_post_success(monkeypatch):
    post_title = "Foo"
    content = "ThisBody"
    category = "[whereitgoes]"
    wp = WP()
    wp._header = {"Authorization": "Bearer exampleToken"}

    def _mock_post(url, headers, json):
        assert url == "https://public-api.wordpress.com/rest/v1.1/sites/abc/posts/new"
        assert headers["Authorization"] == "Bearer exampleToken"
        assert json == {"title": post_title, "content": content, "categories": category}

        class Response:
            def json():
                return {"ID": 123, "URL": "https://localhost/123"}

        return Response

    monkeypatch.setattr("requests.post", _mock_post)
    id, url = wp.post("abc", post_title, content, category)
    assert id == 123
    assert url == "https://localhost/123"


def test_delete_post(monkeypatch):
    count_post_called = 0
    count_get_called = 0
    site = "abc"
    id = 123
    wp = WP()
    wp._header = {"Authorization": "Bearer exampleToken"}

    def _mock_get(url, headers):
        nonlocal count_get_called
        count_get_called += 1
        assert url == "https://public-api.wordpress.com/rest/v1.1/sites/abc/posts/123"

        @dataclass
        class GetResponse:
            status_code: int
            post_status: str = None

            def json(cls):
                return {"status": cls.post_status}

        if count_get_called == 1:
            return GetResponse(status_code=200, post_status=PostStatus.PUBLISH.value)
        else:
            return GetResponse(status_code=404)

    def _mock_post(url, headers):
        nonlocal count_post_called
        count_post_called += 1
        assert (
            url
            == "https://public-api.wordpress.com/rest/v1.1/sites/abc/posts/123/delete"
        )

        @dataclass
        class PostResponse:
            status_code: int

        if count_post_called == 1:
            return PostResponse(status_code=200)
        return PostResponse(status_code=404)

    monkeypatch.setattr("requests.get", _mock_get)
    monkeypatch.setattr("requests.post", _mock_post)
    assert wp.delete_post(site, id)
    assert count_post_called == 2


def test_delete_post_unauthorized(monkeypatch):
    count_called = 0
    site = "abc"
    id = 123
    wp = WP()
    wp._header = {"Authorization": "Bearer exampleToken"}

    def _mock_get(url, headers):
        class GetResponse:
            status_code = 200

            def json(self):
                return {"status": "publish"}

        return GetResponse()

    def _mock_post(url, headers):
        nonlocal count_called
        count_called += 1
        assert (
            url
            == "https://public-api.wordpress.com/rest/v1.1/sites/abc/posts/123/delete"
        )

        class Response:
            status_code = 404

        return Response

    monkeypatch.setattr("requests.get", _mock_get)
    monkeypatch.setattr("requests.post", _mock_post)
    assert not wp.delete_post(site, id)
    assert count_called == 1


def test_get_post_status(monkeypatch):
    """Validate when returned status code != 200, 404

    200 & 404 responses are actually tested above in the delete_post testing which is
    closer to integration than unit. Mocked requests call in the get_post_status fnx
    up there.
    """
    site = "abc"
    id = 123
    wp = WP()
    wp._header = {"Authorization": "Bearer exampleToken"}

    def _mock_get(url, headers):
        class GetResponse:
            status_code = 401

        return GetResponse()

    monkeypatch.setattr("requests.get", _mock_get)
    with pytest.raises(RuntimeError):
        wp.get_post_status(site, id)
