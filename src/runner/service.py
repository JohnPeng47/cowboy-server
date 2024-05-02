from cowboy_lib.repo.repository import PatchFile
from cowboy_lib.coverage import CoverageResult
from cowboy_lib.ast.code import Function
from cowboy_lib.api.runner.shared import RunTestTaskServer

from src.task_queue.service import enqueue_task_and_wait
from src.task_queue.core import TaskQueue

from typing import List, Tuple

from .shared.models import json_to_coverage_result, RunTestTask


async def run_test(
    user_id: int,
    repo_name: str,
    task_queue: TaskQueue,
    exclude_tests: List[Tuple[Function, str]] = [],
    include_tests: List[str] = [],
    patch_file: PatchFile = None,
) -> CoverageResult:

    task = RunTestTask(
        repo_name=repo_name,
        exclude_tests=exclude_tests,
        include_tests=include_tests,
        patch_file=patch_file,
    )

    future = enqueue_task_and_wait(task_queue=task_queue, user_id=user_id, task=task)
    res = await future.wait()

    cov_res = json_to_coverage_result(res)
    return cov_res
