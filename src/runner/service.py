from cowboy_lib.repo.repository import PatchFile
from cowboy_lib.coverage import CoverageResult
from cowboy_lib.ast.code import Function
from cowboy_lib.api.runner.shared import RunTestTaskArgs, FunctionArg

from src.queue.service import enqueue_task_and_wait
from src.queue.core import TaskQueue
from cowboy_lib.api.runner.shared import Task, TaskType

from .models import json_to_coverage_result

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

    # NOTE: problem with including this in RunTestTaskArgs is that exclude_tests
    # will have different signatures before and after validation
    # input: exclude_tests: List[Tuple[Function, str]] = []
    # output (validated): exclude_tests: List[Tuple[FunctionArg, str]] = Field(default_factory=list)
    exclude_tests = [
        (FunctionArg(name=func.name, is_meth=func.is_meth()), str(path))
        for func, path in exclude_tests
    ]

    task = Task(
        repo_name=service_args.repo_name,
        type=TaskType.RUN_TEST,
        task_args=RunTestTaskArgs.from_data(
            patch_file=patch_file,
            exclude_tests=exclude_tests,
            include_tests=include_tests,
        ),
    )

    print("Task: ", task.json())

    future = enqueue_task_and_wait(
        task_queue=service_args.task_queue, user_id=service_args.user_id, task=task
    )
    res = await future.wait()

    cov_res = json_to_coverage_result(res)
    return cov_res
