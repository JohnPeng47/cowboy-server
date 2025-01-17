from abc import ABC, abstractmethod
from src.lib.api.runner.shared import RunTestTaskArgs
from src.lib.coverage import CoverageResult

from typing import Tuple, List, Any


class Runner(ABC):
    """
    Runs the lang/framework specific unit test
    """

    @abstractmethod
    def run_test(self, args: RunTestTaskArgs) -> Tuple[CoverageResult, str, str]:
        """
        Run the test and return the coverage result
        """
        raise NotImplementedError

    def _construct_cmd(
        self,
        repo_path,
        selected_args_str: str = "",
        deselected_args_str: str = "",
    ):
        """
        Constructs the cmd for running the test via subprocess
        """
        raise NotImplementedError

    def _get_include_tests_arg_str(self, include_tests: List[str] = []):
        """
        Constructs the arg string for selecting specific tests
        """
        raise NotImplementedError

    def _get_exclude_tests_arg_str(self, exclude_tests: List[Any]):
        """
        Constructs the arg string for excluding specific tests
        """
        raise NotImplementedError
