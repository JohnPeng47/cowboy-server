from pathlib import Path

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import uuid4
from enum import Enum

from queue import Queue


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass
class Task:
    """
    Database task, tied to a parent job.
    """

    task_id: str = str(uuid4())
    result: dict = dict()
    task_args: dict = dict()
    status: str = TaskStatus.PENDING.value
    name: str = ""


class PytestRunner:
    def __init__(self, user_name: str, repo_path: Path):
        self.user_name = user_name
        self.repo_path = repo_path
