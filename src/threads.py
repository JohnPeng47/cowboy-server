from src.repo.service import get_all, get_or_raise
from src.test_modules.service import get_all_tms
from src.tasks.create_tgt_coverage import create_tgt_coverage
from src.queue.core import get_queue
from src.test_modules.models import TestModuleModel
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


def test_file_to_test_module(db: Session, repo_id: str, file: str) -> TestModuleModel:
    """
    Maps the file back to the test_module. This is a one-to-one mapping
    """
    tms = get_all_tms(db_session=db, repo_id=repo_id)
    for tm in tms:
        if tm.testfilepath == file:
            return tm


def check_github(repo: GitRepo):
    """
    Pulls the remote branch from Github to get diff
    """
    print("Checking for diff in: ", repo.repo_name)
    diff = repo.diff_remote()
    if diff:
        return diff

    return None


def handle_test_files(db: Session, repo, test_files: List[str]):
    """
    Handles the test files
    """
    for file in test_files:
        test_module = test_file_to_test_module(db, repo.id, file)
        if test_module:
            print("Running test: ", test_module.testfilepath)


# TODO: write test for this
def check_for_changed_files(db: Session) -> ChangedFiles:
    """
    Checks for repo update
    """
    while True:
        repos = get_all(db_session=db)
        with ThreadPoolExecutor() as executor:
            for repo in repos:
                future = executor.submit(
                    check_github, GitRepo(Path(repo.source_folder))
                )
                diff = future.result()
                if diff:
                    code_files, test_files = diff.code_files, diff.test_files
                    if test_files:
                        handle_test_files(db, repo, test_files)

        time.sleep(5)
