from cowboy_lib.coverage import CoverageResult, TestCoverage
from cowboy_lib.repo.repository import PatchFile

from pathlib import Path

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


from src.task_queue.models import Task


@dataclass
class FunctionArg:
    name: str
    path: str


@dataclass
class RunTestTaskArgs:
    exclude_tests: List[Tuple[FunctionArg, str]]
    include_tests: List[str]
    patch_file: PatchFile

    def __post_init__(self):
        if self.patch_file:
            self.patch_file.path = str(self.patch_file.path)


class RunTestTask(Task):
    args: Optional[RunTestTaskArgs]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.args = RunTestTaskArgs(*args, **kwargs)


def json_to_coverage_result(payload):
    cov_results = CoverageResult("", "", {})
    cov_results.coverage = TestCoverage.deserialize(payload["coverage"])
    cov_results.failed = payload["failed"]

    return cov_results
