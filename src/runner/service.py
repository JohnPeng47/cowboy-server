from cowboy_lib.repo.repository import PatchFile
from cowboy_lib.coverage import CoverageResult
from cowboy_lib.ast.code import Function

from src.queue.service import enqueue_task_and_wait
from src.queue.core import TaskQueue

from .models import json_to_coverage_result, RunTestTask

from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class RunServiceArgs:
    user_id: int
    repo_name: str
    task_queue: TaskQueue


async def run_test(
    service_args: RunServiceArgs,
    exclude_tests: List[Tuple[Function, str]] = [],
    include_tests: List[str] = [],
    patch_file: PatchFile = None,
) -> CoverageResult:

    print("hello3")
    task = RunTestTask(
        repo_name=service_args.repo_name,
        exclude_tests=exclude_tests,
        include_tests=include_tests,
        patch_file=patch_file,
    )

    future = enqueue_task_and_wait(
        task_queue=service_args.task_queue, user_id=service_args.user_id, task=task
    )
    res = await future.wait()
    print(res)

    cov_res = json_to_coverage_result(res)
    return cov_res
