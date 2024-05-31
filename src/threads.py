from src.repo.service import get_all, get_or_raise
from cowboy_lib.repo.repository import GitRepo
from pathlib import Path

from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
import time
from typing import List


class ChangedFiles:
    code_files: List[str]
    test_files: List[str]
    repo: int


# TODO: write test for this
def check_for_changed_files(db: Session) -> ChangedFiles:
    """
    Checks for repo update
    """

    def check_github(repo: GitRepo):
        print("Checking for diff in: ", repo.repo_name)
        diff = repo.diff_remote()
        if diff:
            return diff

        return None

    while True:
        repo_paths = [
            GitRepo(Path(repo.source_folder)) for repo in get_all(db_session=db)
        ]
        print("Repo paths: ", len(repo_paths))
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(check_github, repo) for repo in repo_paths]
            diffs = [executor.result() for executor in futures]

            for diff in diffs:
                if diff:
                    print("Diff: ", diff.code_files, diff.test_files)

        time.sleep(5)
