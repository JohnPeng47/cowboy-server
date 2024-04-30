from enum import Enum

from pydantic import BaseModel
from typing import List, Annotated, Optional, Any

from src.utils import generate_id


class TaskStatus(Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


from pydantic import Field


class Task(BaseModel):
    """
    Task datatype
    """

    repo_name: str
    task_id: str = Field(default_factory=lambda: generate_id())
    result: dict = Field(default_factory=dict)
    status: str = Field(default=TaskStatus.PENDING.value)
    args: Optional[Any]


class CompleteTaskRequest(Task):
    pass


class GetTaskResponse(Task):
    pass
