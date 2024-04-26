from uuid import uuid4
from enum import Enum

from pydantic import BaseModel
from typing import List


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


from pydantic import Field


class Task(BaseModel):
    """
    Task datatype
    """

    repo_name: str
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    result: dict = Field(default_factory=dict)
    status: str = Field(default=TaskStatus.PENDING.value)


class ListTasks(BaseModel):
    tasks: List[Task]
