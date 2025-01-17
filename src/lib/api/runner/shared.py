from src.lib.utils import generate_id
from src.lib.ast.code import Function
from src.lib.repo.repository import PatchFile

from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import List, Optional, Any, Tuple, Dict
from enum import Enum
from pathlib import Path


class TaskStatus(Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class TaskType(str, Enum):
    SHUTDOWN = "SHUTDOWN"
    RUN_TEST = "RUN_TEST"


class TaskResult(BaseModel):
    coverage: Optional[Dict] = None
    failed: Optional[Dict] = None
    exception: Optional[str] = None

    @model_validator(mode="before")
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

    type: TaskType
    task_id: str = Field(default_factory=lambda: generate_id())
    result: Optional[TaskResult] = Field(default=None)
    status: str = Field(default=TaskStatus.PENDING.value)
    task_args: Optional[Any] = Field(default=None)


class FunctionArg(BaseModel):
    name: str
    is_meth: bool


# each classmethod below accepts different signatures which are inconsistent
# with the class fields of the Pydantic BaseModel, so we had to set the
# class fields to Any... need better way of expressing this
class RunTestTaskArgs(BaseModel):
    repo_name: str
    patch_file: Optional[Any] = None
    exclude_tests: List[Tuple[Any, Any]] = Field(default_factory=list)
    include_tests: List[str] = Field(default_factory=list)

    @classmethod
    def from_data(
        cls,
        repo_name: str,
        exclude_tests: List[Tuple[Tuple[str, bool], str]] = [],
        include_tests: List[str] = [],
        patch_file: PatchFile = None,
    ):
        """
        Used by server
        """
        partial = cls(
            repo_name=repo_name,
            patch_file=patch_file,
            exclude_tests=exclude_tests,
            include_tests=include_tests,
        )

        if partial.exclude_tests:
            partial.exclude_tests = [
                (
                    FunctionArg(
                        name=func[0],
                        is_meth=func[1],
                    ),
                    str(path),
                )
                for func, path in partial.exclude_tests
            ]

        return partial

    @classmethod
    def from_json(
        cls,
        repo_name: str,
        patch_file: Dict = {},
        exclude_tests: List[Tuple[Dict, str]] = [],
        include_tests: List[str] = [],
    ):
        """
        Used by client
        """
        partial = cls(
            repo_name=repo_name,
            patch_file=patch_file,
            exclude_tests=exclude_tests,
            include_tests=include_tests,
        )

        if partial.patch_file:
            partial.patch_file = PatchFile(
                path=Path(partial.patch_file["path"]),
                patch=partial.patch_file["patch"],
            )
        if partial.exclude_tests:
            partial.exclude_tests = [
                (
                    FunctionArg(
                        name=func[0],
                        is_meth=func[1],
                    ),
                    Path(path),
                )
                for func, path in partial.exclude_tests
            ]

        return partial
