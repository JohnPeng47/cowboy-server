import requests
from typing import Tuple, List, Optional
import time
from logging import getLogger
import os

from dataclasses import dataclass, field

from git import Diff

# is this the right way? Feel like proper way is to load config
# at single point upstream and then pass it down .. but idk
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

logger = getLogger("test_results")


class GithubAPI:
    access_token = GITHUB_TOKEN

    def _make_github_api_request(self, url: str):
        headers = {
            "Authorization": f"token {self.access_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        response = requests.get(url, headers=headers)
        remaining_rate_limit = int(response.headers.get("X-RateLimit-Remaining", 0))
        if remaining_rate_limit < 10:
            print("Rate limit exceeded, sleeping for 15 seconds")
            time.sleep(15)

        return response

    @classmethod
    def fork_repository(cls, repo_full_name: str) -> str:
        """
        Forks the given repository.

        Parameters:
        - repo_full_name: The full name of the repository to fork (e.g., "owner/repo_name").

        Returns:
        The URL of the forked repository or None if the request fails.
        """
        url = f"https://api.github.com/repos/{repo_full_name}/forks"
        headers = {
            "Authorization": f"token {cls.access_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        response = requests.post(url, headers=headers)
        if response.status_code in [202, 201]:  # 202 Accepted or 201 Created
            forked_repo_url = response.json().get("html_url")
            return forked_repo_url
        else:
            print(
                f"Failed to fork the repository {repo_full_name}. Status code: {response.status_code}"
            )
            return None


def fork_repo(url) -> str:
    return GithubAPI.fork_repository(url)
