from lib.repo.repository import PatchFile

from src.runner.models import FunctionArg, RunTestTask
from src.task_queue.models import Task
from src.task_queue.service import enqueue_task
from src.task_queue.core import TaskQueue

from typing import List, Tuple
from pathlib import Path


def run_test(
    user_id: int,
    repo_name: str,
    task_queue: TaskQueue,
    exclude_tests: List[Tuple[FunctionArg, str]] = [],
    include_tests: List[str] = [],
    patch_file: PatchFile = None,
) -> None:
    """Run the test suite."""
    task = RunTestTask(
        repo_name=repo_name,
        exclude_tests=exclude_tests,
        include_tests=include_tests,
        patch_contents=patch_file.patch if patch_file else "",
        patch_file_path=patch_file.path if patch_file else "",
    )

    enqueue_task(task_queue=task_queue, user_id=user_id, task=task)
