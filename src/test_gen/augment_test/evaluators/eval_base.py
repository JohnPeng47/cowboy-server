from src.lib.coverage import CoverageResult, TestError, TestCoverage
from src.lib.repo.repository import PatchFile
from src.lib.repo.source_file import Function, TestFile

from src.runner.service import RunServiceArgs
from src.logger import testgen_logger as log

from pathlib import Path
from abc import ABC, abstractmethod
from typing import Callable, Tuple, List, TYPE_CHECKING
if TYPE_CHECKING:
    from test_gen.augment_test.types import StratResult
    from src.lib.test_modules import TestModule
    from src.lib.repo.source_repo import SourceRepo


class Evaluator(ABC):
    def __init__(
        self, 
        repo_name: str, 
        src_repo: "SourceRepo", 
        run_args: RunServiceArgs,
        tm: "TestModule",
        run_test: Callable,
        use_cache = False,
        delete_last = False
    ):
        self.repo_name = repo_name
        self.src_repo = src_repo
        self.run_args = run_args
        self.run_test = run_test
        self.tm = tm
        self.use_cache = use_cache
        self.delete_last = delete_last

    async def diff_coverage(
        self,
        strat_results: List["StratResult"],
        module_cov: TestCoverage,
        test_fp: Path,
        n_times: int = 1,
    ) -> List[Tuple[CoverageResult, TestCoverage]]:
        """
        Finds the coverage difference between the module coverage and the coverage
        """
        test_results = []
        total_cost = 0
        
        for i, (test_file, test_funcs) in enumerate(strat_results, start=1):
            patch_file = PatchFile(path=test_fp, patch=test_file)
            newtest_cov = await self.run_test(
                self.repo_name, 
                self.run_args, 
                include_tests=self.tm,
                patch_file=patch_file, 
                use_cache=self.use_cache,
                delete_last=self.delete_last
            )
            cov_diff = newtest_cov.get_coverage() - module_cov
            if cov_diff.total_cov.covered < 0:
                log.info(f"Negative coverage, skipping")
                continue
            # TODO: this covered number is off check
            log.info(f"Module cov: {module_cov}")
            log.info(f"Newtest cov: {newtest_cov.get_coverage()}")
            log.info(
                f"New coverage from generated tests: {cov_diff.total_cov.covered}"
            )
            test_results.append((newtest_cov, cov_diff, test_file))

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
        new_funcs = old_testfile.diff_test_funcs(new_testfile)

        return new_funcs

    @abstractmethod
    async def __call__(
        self,
        llm_results: List["StratResult"],
        tm: "TestModule",
        module_cov: CoverageResult,
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
