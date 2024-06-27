from cowboy_lib.repo.repository import PatchFile
from cowboy_lib.coverage import CoverageResult
from cowboy_lib.ast.code import Function

from cowboy_lib.api.runner.shared import (
    Task,
    TaskType,
    RunTestTaskArgs,
    FunctionArg,
)
from src.queue.service import enqueue_task_and_wait
from src.queue.core import TaskQueue

from .models import json_to_coverage_result

from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class RunServiceArgs:
    user_id: int
    task_queue: TaskQueue


async def run_test(
    repo_name: str,
    service_args: RunServiceArgs,
    exclude_tests: List[Tuple[Function, str]] = [],
    include_tests: List[str] = [],
    patch_file: PatchFile = None,
) -> CoverageResult:
    task = Task(
        type=TaskType.RUN_TEST,
        task_args=RunTestTaskArgs(
            repo_name=repo_name,
            patch_file=patch_file,
            exclude_tests=[((f.name, f.is_meth()), path) for f, path in exclude_tests],
            include_tests=include_tests,
        ),
    )

    future = enqueue_task_and_wait(
        task_queue=service_args.task_queue,
        user_id=service_args.user_id,
        task=task,
    )
    res = await future.wait()

    cov_res = json_to_coverage_result(res)
    return cov_res


async def shutdown_client(
    service_args: RunServiceArgs,
) -> CoverageResult:
    task = Task(type=TaskType.SHUTDOWN)

    future = enqueue_task_and_wait(
        task_queue=service_args.task_queue,
        user_id=service_args.user_id,
        task=task,
    )

    await future.wait(timeout=3)
