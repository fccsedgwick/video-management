from operator import attrgetter
from os import getenv
from os import path
from os import remove
from re import match
from tempfile import gettempdir
from typing import List

import requests
from github3 import login
from github3.repos.release import Release
from github3.repos.repo import Repository

from gpg.gpg import GPGSigning


class Github:
    def __init__(self) -> None:
        self._gh = login("fccsedgwick", password=getenv("GH_TOKEN"))

    @property
    def repo(self) -> Repository:
        """github3.repos.repo.Repository object"""
        return self._repo

    @repo.setter
    def repo(self, new_repo: str) -> None:
        """Set new GitHub Repo

        Args:
            new_repo (str): string describing repo in typical <owner>/<repo> format
                            (e.g. "fccsedgwick/post-lambda")

        Raises:
            ValueError: new_repo string does not match expected format. Owner
                        is expected to be alphabetic and repo is expected to be
                        alphanumeric with '-'
        """
        if not match("^[a-zA-z]+/[a-zA-Z0-9-]+", new_repo):
            raise ValueError("repo does not match expected pattern (<owner>/<repo>)")
        (owner, repo) = new_repo.split("/")
        self._repo = self._gh.repository(owner, repo)

    def get_signed_assets_from_release(
        self, release: Release, filenames: List[str]
    ) -> List[str]:
        """Returns list of files which were signed

        All filenames and matching <filename>.sig files found in a release
        will be downloaded if the sig file is verified by `gpg.GPGSigning` then
        the sig file will be deleted and the filename will be returned to the
        caller. If the sig file is invalid for the given filename both filename
        and matching sig file will be deleted. No other indication to the
        caller is given about signature failing other than the file not being
        in the returned list.

        Args:
            release (github3.repos.release.Release): release from which to
                    retrieve assets
            filenames (List[str]): list of os.path str-like references to
                    download

        Returns:
            List[str]: list of assets (from filenames) that were downloaded and
                       signed
        """
        assets = []
        for filename in filenames:
            if filename.endswith(".sig"):
                continue
            release_asset = None
            release_asset_sig = None
            for asset in release.original_assets:
                if asset.name == filename:
                    release_asset = asset
                elif asset.name == f"{filename}.sig":
                    release_asset_sig = asset
            if release_asset is None or release_asset_sig is None:
                continue
            asset = path.join(gettempdir(), release_asset.name)
            asset_sig = path.join(gettempdir(), release_asset_sig.name)
            release_asset.download(asset)
            release_asset_sig.download(asset_sig)
            if GPGSigning().verify_signature(artifact=asset, signature=asset_sig):
                assets.append(asset)
            else:
                remove(asset)
            remove(asset_sig)
        return assets

    def get_latest_signed_assets(self, filenames: List[str]) -> List[str]:
        """Get the given filenames from the latest GitHub release

        Additional constraint is that all filenames requested must be:
            a) assets on the release
            b) have a valid detached signature in the format <filename>.sig
               that is also an asset on the GitHub release
        If the constraints are not met on the most current release, the next
        prior release will be checked

        precondition: `class.repo` attribute has been set.

        Args:
            filenames (List[str]): the list of filnames (assets) to retrieve
                                   from the release

        Returns:
            List[str]: the subset of filenames that have a valid signature
        """
        releases = sorted(
            list(self.repo.releases()), key=attrgetter("created_at"), reverse=True
        )
        for release in releases:
            assets = self.get_signed_assets_from_release(release, filenames)
            if len(assets) == len(filenames):
                break
        return assets
