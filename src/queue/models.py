from cowboy_lib.utils import generate_id

from pydantic import BaseModel, Field, ConfigDict, root_validator
from typing import Optional, Any, Dict
from enum import Enum


class TaskStatus(Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class TaskResult(BaseModel):
    coverage: Optional[Dict] = None
    failed: Optional[Dict] = None
    exception: Optional[str] = None

    @root_validator
    def check_coverage_or_exception(cls, values):
        coverage, failed, exception = (
            values.get("coverage"),
            values.get("failed"),
            values.get("exception"),
        )
        if exception and (coverage or failed):
            raise ValueError(
                "If 'exception' is specified, 'coverage' and 'failed' must not be specified."
            )
        if not exception and not (coverage or failed):
            raise ValueError(
                "Either 'coverage' and 'failed' or 'exception' must be specified."
            )
        return values


class Task(BaseModel):
    """
    Task datatype
    """

    config = ConfigDict(arbitrary_types_allowed=True)

    repo_name: str
    task_id: str = Field(default_factory=lambda: generate_id())
    result: Optional[TaskResult] = Field(default=None)
    status: str = Field(default=TaskStatus.PENDING.value)
    task_args: Optional[Any]


class CompleteTaskRequest(Task):
    pass


class GetTaskResponse(Task):
    pass
