from cowboy_lib.repo.repository import GitRepo
from cowboy_lib.repo.diff import DiffMode

from src.queue.core import TaskQueue
from src.repo.service import get_all, get_or_raise
from src.repo.models import RepoConfig
from src.test_modules.service import get_all_tms
from src.tasks.create_tgt_coverage import create_tgt_coverage
from src.queue.core import get_queue
from src.test_modules.models import TestModuleModel

from src.logger import sync_repo as log

from pathlib import Path
import asyncio
from sqlalchemy.orm import Session
from typing import List
import threading


class ChangedFiles:
    code_files: List[str]
    test_files: List[str]
    repo: int


def start_sync_thread(db_session: Session, task_queue: TaskQueue):
    def run_async_thread(loop, func, *args):
        """
        Helper func to run async functions in a new thread
        """
        asyncio.set_event_loop(loop)
        loop.run_until_complete(func(*args))

    threading.Thread(
        target=run_async_thread,
        args=(
            asyncio.new_event_loop(),
            check_for_changed_files,
            db_session,
            task_queue,
        ),
        daemon=True,
    ).start()


def testfile_to_tm(db: Session, repo_id: str, file: str) -> TestModuleModel:
    """
    Maps the file back to the test_module. This is a one-to-one mapping
    """
    tms = get_all_tms(db_session=db, repo_id=repo_id)
    for tm in tms:
        if tm.testfilepath == file:
            return tm

    return None


def srcfile_to_tm(db: Session, repo_id: str, file: str) -> TestModuleModel:
    """
    Maps the src file back to test_module. This is n-to-one mapping
    """
    tms = get_all_tms(db_session=db, repo_id=repo_id)
    for tm in tms:
        if file in tm.get_covered_files():
            return tm

    return None


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
async def handle_modified_test_files(
    db_session: Session, repo: RepoConfig, test_files: List[str]
):
    """
    Handles the test files
    """
    task_queue = get_queue()
    tm_models = [testfile_to_tm(db_session, repo.id, file) for file in test_files]

    await create_tgt_coverage(
        db_session=db_session,
        task_queue=task_queue,
        repo_config=repo,
        tm_models=tm_models,
    )


def is_test_file(path: str):
    return Path(path).name.startswith("test_")


async def check_for_changed_files(
    db_session: Session, task_queue: TaskQueue
) -> ChangedFiles:
    """
    Checks for repo update
    """
    while True:
        repos = get_all(db_session=db_session)
        for repo in repos:
            git_repo = GitRepo(Path(repo.source_folder))
            commit = git_repo.diff_remote()

            for diff in commit.diffs:
                if diff.attrs.mode == DiffMode.MODIFIED:
                    modified_file = diff.attrs.a_path
                    impacted_tm = (
                        testfile_to_tm(db_session, repo.id, modified_file)
                        if is_test_file(modified_file)
                        else srcfile_to_tm(db_session, repo.id, modified_file)
                    )
                    log.info(f"Impacted tm: {impacted_tm.name}")

                    if not impacted_tm:
                        # TODO: this is actually really bad, because it implies that we are
                        # missing some kind of update to the repo
                        continue

                    await create_tgt_coverage(
                        db_session=db_session,
                        task_queue=task_queue,
                        repo=repo,
                        tm_models=[impacted_tm],
                        overwrite=True,
                    )

        # async with ThreadPoolExecutor() as executor:
        #     loop = asyncio.get_event_loop()
        #     tasks = [
        #         loop.run_in_executor(
        #             executor, check_github, GitRepo(Path(repo.source_folder))
        #         )
        #         for repo in repos
        #     ]

        #     for task, repo in zip(tasks, repos):
        #         diff = await task
        # if diff:
        #     code_files, test_files = diff.code_files, diff.test_files
        #     if test_files:
        #         await handle_test_files(db, repo, test_files)

        await asyncio.sleep(10)
