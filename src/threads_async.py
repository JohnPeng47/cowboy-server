from src.repo.service import get_all, get_or_raise
from src.test_modules.service import get_all_tms
from src.tasks.create_tgt_coverage import create_tgt_coverage
from src.queue.core import get_queue
from src.test_modules.models import TestModuleModel
from cowboy_lib.repo.repository import GitRepo
from pathlib import Path

import asyncio
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


# TODO: make sure this executes in parallel wrt to different
# repos
async def check_github(repo: GitRepo):
    """
    Pulls the remote branch from Github to get diff
    """
    print("Checking for diff in: ", repo.repo_name)
    diff = repo.diff_remote()
    if diff:
        return diff

    return None


# TODO: ideally we would have mechanism to queue a task to be run next time a
# client connects, should they not be currently connected
async def handle_test_files(db_session: Session, repo, test_files: List[str]):
    """
    Handles the test files
    """
    tm_names = []
    for file in test_files:
        test_module = test_file_to_test_module(db_session, repo.id, file)
        tm_names.append(test_module.name)

    print("RE-Baselining: ", tm_names)
    await create_tgt_coverage(
        db_session=db_session,
        task_queue=get_queue(),
        repo_config=repo,
        tm_names=tm_names,
    )


# TODO: write test for this
async def check_for_changed_files(db: Session) -> ChangedFiles:
    """
    Checks for repo update
    """
    while True:
        repos = get_all(db_session=db)
        async with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(
                    executor, check_github, GitRepo(Path(repo.source_folder))
                )
                for repo in repos
            ]

            for task, repo in zip(tasks, repos):
                diff = await task
                if diff:
                    code_files, test_files = diff.code_files, diff.test_files
                    if test_files:
                        await handle_test_files(db, repo, test_files)
        time.sleep(5)
