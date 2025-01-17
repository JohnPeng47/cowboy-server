from src.lib.coverage import CoverageResult, TestError, TestCoverage
from src.lib.repo.repository import PatchFile
from src.lib.repo.source_file import Function, TestFile

from typing import Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from test_gen.augment_test.types import StratResult
    from src.lib.test_modules import TestModule

from .eval_base import Evaluator

from src.logger import testgen_logger as log

class AugmentAdditiveEvaluator(Evaluator):
    """
    Iteratively evals test results and re-prompts with partially successful
    test file to **attempt** to get additive coverage
    """

    async def __call__(
        self,
        llm_results: List["StratResult"],
        tm: "TestModule",
        module_cov: TestCoverage,
        updated_testfile: TestFile,
        n_times: int = 1,
    ) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
        "TestModule",
    ]:
        """
        Main eval method, accepts a list of results from the strategy and the
        targeted test module, and a baseline coverage to compare against
        """
        test_fp = tm.test_file.path
        improved, failed, no_improve = await self.process_test_results(
            llm_results, tm, module_cov, updated_testfile
        )

        return improved, failed, no_improve

    async def process_test_results(
        self,
        llm_results: List["StratResult"],
        tm: "TestModule",
        module_cov: TestCoverage,
        updated_testfile: TestFile,
    ) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:
        """
        Sequentially build a set of coverage improving testcases, discarding any
        generated tests that dont contribute coverage improvements
        """
        improved_tests: List[Tuple[Function, TestCoverage]] = []
        failed_tests: List[Tuple[Function, TestError]] = []
        noimprov_tests: List[Function] = []

        for test_contents, test_fp in llm_results:
            new_funcs = self.get_new_funcs(test_contents, tm.path)

            log.info(f"Generated {len(new_funcs)} new funcs: {new_funcs}")

            for func in new_funcs:
                # collect coverage for one test at a time and compare to module coverage
                # we have to use the updated testfile because module_cov is based on the updated functions 
                og_testfile = updated_testfile.clone()
                og_testfile.append(
                    # NEWTODO(BUG1): ideally we should have to lstrip here
                    func.to_code().lstrip(), class_name=func.scope.name if func.scope else ""
                )
                patch_file = PatchFile(
                    path=str(tm.path), patch=og_testfile.to_code()
                )
                indvtest_cov = await self.run_test(
                    self.repo_name,
                    self.run_args,
                    include_tests=tm,
                    patch_file=patch_file,
                    use_cache=self.use_cache,
                    delete_last=self.delete_last
                )

                test_error = indvtest_cov.get_failed(func.name)
                
                if test_error:
                    log.info(f"[FAILED] Generated Func: ")
                    log.info({func.name})
                    log.info(f"Failed func: {func.to_code().lstrip()}")
                    # log.info(f"Patchfile: {og_testfile.to_code()}")

                    failed_tests.append((func, test_error))
                    continue

                log.info(f"IndvTest Coverage: {indvtest_cov.get_coverage()}")
                log.info(f"Module Coverage: {module_cov}")

                indv_improve = indvtest_cov.get_coverage() - module_cov
                if indv_improve.total_cov.covered > 0:
                    log.info(f"[IMPROVE] Generated Func: ")
                    log.info(func.name)
                    log.info(f"Improved func: {func.to_code().lstrip()}")
                    # log.info(f"Patchfile: {og_testfile.to_code()}")

                    improved_tests.append((func, indv_improve))
                else:
                    log.info(f"[NOIMPROVE] Generated Func: ")
                    log.info({func.name})
                    log.info(f"No improve func: {func.to_code().lstrip()}")
                    # log.info(f"Patchfile: {og_testfile.to_code()}")

                    noimprov_tests.append((func, TestCoverage([])))


        return improved_tests, failed_tests, noimprov_tests
