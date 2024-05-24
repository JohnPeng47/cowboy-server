# shared\models contain "IPC" interface between client and server, which for now
# is just the run_test interface
from cowboy_lib.coverage import CoverageResult, TestCoverage
from cowboy_lib.api.runner.shared import RunTestTaskServer, TaskResult
from fastapi import HTTPException

from src.models import CowboyBase
from src.queue.models import Task

from pydantic import BaseModel


class RunTestTask(RunTestTaskServer, CowboyBase):
    pass


class ClientRunnerException(HTTPException):
    def __init__(self, msg):
        self.detail = msg
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
