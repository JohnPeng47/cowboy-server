from src.lib.repo.repository import PatchFile
from src.lib.coverage import CoverageResult, TestCoverage
from src.lib.api.runner.shared import TaskResult

from fastapi import HTTPException
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass

from src.queue.core import TaskQueue

class ClientRunnerException(HTTPException):
    def __init__(self, msg):
        # TODO: make pytest a variable for diff testing frameworks
        self.detail = f"Local pytest runner error: {msg}"
        self.status_code = 400


class RunnerExceptionResponse(BaseModel):
    exception: str


def json_to_coverage_result(res: TaskResult):
    if res.exception:
        raise ClientRunnerException(res.exception)

    cov_results = CoverageResult("", "", {})
    cov_results.coverage = TestCoverage.deserialize(res.coverage)
    cov_results.failed = res.failed

    return cov_results

@dataclass
class RunServiceArgs:
    user_id: int
    task_queue: TaskQueue