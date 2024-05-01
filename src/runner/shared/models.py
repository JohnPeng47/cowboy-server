# shared\models contain "IPC" interface between client and server, which for now
# is just the run_test interface
from cowboy_lib.ast.code import Function
from cowboy_lib.coverage import CoverageResult, TestCoverage
from cowboy_lib.repo.repository import PatchFile

from cowboy_lib.api.runner.shared import RunTestTaskServer

from src.models import CowboyBase


from src.task_queue.models import Task


class RunTestTask(RunTestTaskServer, CowboyBase):
    pass


def json_to_coverage_result(payload):
    cov_results = CoverageResult("", "", {})
    cov_results.coverage = TestCoverage.deserialize(payload["coverage"])
    cov_results.failed = payload["failed"]

    return cov_results
