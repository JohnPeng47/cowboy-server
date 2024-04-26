from pathlib import Path

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import uuid4
from enum import Enum

from queue import Queue

from contextlib import contextmanager
import queue


class RunnerQueue:
    """
    Executes the test suite before and after a diff is applied,
    and compares the results. Runs in two modes: full and selective.
    In full mode, the full test suite is run.
    In selective mode, only selected test cases.
    """

    def __init__(self):
        pass

    def run_test(
        self,
        exclude_tests: List[Tuple[Function, Path]] = [],
        include_tests: List[str] = [],
        patch_file: PatchFile = None,
        git_repo: GitRepo = None,
        cache=False,
    ) -> Tuple[CoverageResult, str, str]:
        return (
            cov,
            stdout,
            stderr,
        )
