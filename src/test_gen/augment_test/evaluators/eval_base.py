from cowboy_lib.coverage import CoverageResult, TestError, TestCoverage
from cowboy_lib.repo.repository import PatchFile
from cowboy_lib.repo.source_file import Function, TestFile

from src.runner.service import run_test, RunServiceArgs
from src.logger import testgen_logger
from typing import Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from test_gen.augment_test.types import StratResult
    from cowboy_lib.test_modules import TestModule
    from cowboy_lib.repo.source_repo import SourceRepo

from pathlib import Path
from abc import ABC, abstractmethod


class Evaluator(ABC):
    def __init__(
        self, repo_name: str, src_repo: "SourceRepo", run_args: RunServiceArgs
    ):
        self.repo_name = repo_name
        self.src_repo = src_repo
        self.run_args = run_args

    async def gen_test_and_diff_coverage(
        self,
        strat_results: List["StratResult"],
        base_cov: TestCoverage,
        test_fp: Path,
        n_times: int = 1,
    ) -> List[Tuple[CoverageResult, TestCoverage]]:
        """
        Does two runs:
        1. Run to get coverage baseline
        2. Run with generated test case
        Return diff in coverage, and generated test case
        """
        test_results = []
        total_cost = 0

        # WARNING: for some reason failures here are not recorded fully for every new individual
        # that is generate. Possibly due to failures cascading?
        for i, (test_file, test_funcs) in enumerate(strat_results, start=1):
            patch_file = PatchFile(path=test_fp, patch=test_file)
            cov_ptched = await run_test(
                self.repo_name, self.run_args, patch_file=patch_file
            )
            cov_diff = cov_ptched.coverage - base_cov
            # TODO: this covered number is off check
            testgen_logger.info(
                f"New coverage from generated tests: {cov_diff.total_cov.covered}"
            )
            test_results.append((cov_ptched, cov_diff, test_file))

        return test_results

    def get_new_funcs(
        self,
        new_testfile: str,
        test_fp: Path,
    ) -> List[Function]:
        """
        Get newly generated functions
        """
        new_testfile = TestFile(lines=new_testfile.split("\n"), path=str(test_fp))
        old_testfile: TestFile = self.src_repo.find_file(test_fp)
        new_funcs = old_testfile.new_test_funcs(new_testfile)

        return new_funcs

    @abstractmethod
    async def __call__(
        self,
        llm_results: List["StratResult"],
        tm: "TestModule",
        base_cov: CoverageResult,
        n_times: int = 1,
    ):
        raise NotImplementedError

    @abstractmethod
    async def process_test_results(
        self,
        test_results: List[Tuple[CoverageResult, str]],
        tm: "TestModule",
        del_cov: CoverageResult,
    ) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:
        raise NotImplementedError
