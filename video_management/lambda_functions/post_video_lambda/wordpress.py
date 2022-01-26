from enum import Enum
from typing import Tuple

import requests


class PostStatus(Enum):
    PUBLISH = "publish"
    DRAFT = "draft"
    PENDING = "pending"
    PRIVATE = "private"
    FUTURE = "future"
    TRASH = "trash"
    AUTO_DRAFT = "auto-draft"
    # Not a WP post status
    NOT_FOUND = "not-found"


class WP:

    _api = "https://public-api.wordpress.com/rest/v1.1/sites/"
    _token_url = "https://public-api.wordpress.com/oauth2/token"
    _header = None

    def _url(self, site_id: int, endpoint: str) -> str:
        return f"{self._api}{site_id}/{endpoint}"

    def login(
        self, client_id: int, client_secret: str, username: str, password: str
    ) -> None:
        """Logs into a WordPress app and sets authorization headers for future calls.

        Args:
            client_id (int): WordPress app client id for OAuth authentication
            client_secret (str): WordPressapp client secret for OAuth authentication
            username (str): Username for WordPress account that will make posts
            password (str): Passowrd for WordPress account that will make posts

        Raises:
            PermissionError: Failed to login.
        """
        response = requests.post(
            url=self._token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "username": username,
                "password": password,
                "grant_type": "password",
            },
        )
        if response.status_code == 400:
            raise PermissionError(f"Cannot login to WordPress - {response.json()}")
        self._header = {"Authorization": f"Bearer {response.json()['access_token']}"}

    def post(
        self,
        site_id: int,
        title: str,
        content: str,
        category: str,
        status: str = "publish",
    ) -> Tuple[int, str]:
        """Make a WordPress Site post

        Args:
            site_id (int): Site Id of the WordPress site to post to
            title (str): Title of the post
            content (str): body of the post
            category (str): Catgory that the post should be tagged
            status (str, optional): Post status to set (e.g. publish, draft). Defaults
                                    to "publish".

        Returns:
            Tuple[int, str]: id of the post, url to the post
        """
        # TODO: Handle Failure
        body = {"title": title, "content": content, "categories": category}
        response = requests.post(
            url=self._url(site_id=site_id, endpoint="posts/new"),
            headers=self._header,
            json=body,
        )
        return response.json()["ID"], response.json()["URL"]

    def get_post_status(self, site_id: int, id: int) -> PostStatus:
        """Retrieve the status of a post

        Args:
            site_id (int): WordPress Site Id of the post to check
            id (int): Id of the post

        Raises:
            NotFoundErr: The post does not exist

        Returns:
            PostStatus: Post's status
        """
        response = requests.get(
            url=self._url(site_id=site_id, endpoint=f"posts/{id}"), headers=self._header
        )
        if response.status_code == 200:
            return PostStatus(response.json()["status"])
        elif response.status_code == 404:
            return PostStatus.NOT_FOUND
        raise RuntimeError

    def delete_post(self, site_id: int, id: int) -> bool:
        """Delete a WordPress post.

        WordPress has a trash bin to work through. Takes two deletes.
        Args:
            site_id (int): WordPress Site Id of the post to check
            id (int): Id of the post

        Returns:
            bool: Whether the post was deleted or not.
        """
        post_status = self.get_post_status(site_id, id)
        if post_status == PostStatus.NOT_FOUND:
            iterations = 0
        elif post_status == PostStatus.TRASH:
            iterations = 1
        else:
            iterations = 2

        while iterations > 0:
            response = requests.post(
                url=self._url(site_id=site_id, endpoint=f"posts/{id}/delete"),
                headers=self._header,
            )
            iterations -= 1
            # 404 is permission denied, no reason to try multiple times
            if response.status_code == 404:
                iterations = 0
        return self.get_post_status(site_id, id) == PostStatus.NOT_FOUND
