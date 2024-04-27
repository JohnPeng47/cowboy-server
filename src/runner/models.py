from pathlib import Path

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


from lib.repo.repository import PatchFile

from src.task_queue.models import Task


@dataclass
class FunctionArg:
    name: str
    path: str


@dataclass
class RunTestTaskArgs:
    exclude_tests: List[Tuple[FunctionArg, str]]
    include_tests: List[str]
    patch_contents: str
    patch_file_path: str


class RunTestTask(Task):
    args: Optional[RunTestTaskArgs]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.args = RunTestTaskArgs(*args, **kwargs)
