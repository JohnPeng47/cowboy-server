from cowboy_lib.coverage import CoverageResult, TestError, TestCoverage
from cowboy_lib.repo.repository import PatchFile
from cowboy_lib.repo.source_file import Function

from typing import Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from test_gen.augment_test.types import StratResult
    from cowboy_lib.test_modules import TestModule

from .eval_base import Evaluator

from concurrent.futures import ThreadPoolExecutor
from src.logger import testgen_logger


class AugmentParallelEvaluator(Evaluator):
    """
    Used to evaluate the results of a test strategy
    """

    async def __call__(
        self,
        llm_results: List["StratResult"],
        tm: "TestModule",
        base_cov: CoverageResult,
        n_times: int = 1,
    ) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:
        """
        Main eval method, accepts a list of results from the strategy and the
        targeted test module, and a baseline coverage to compare against
        """
        test_fp = tm.test_file.path
        test_results = await self.gen_test_and_diff_coverage(
            llm_results, base_cov, test_fp, n_times
        )
        improved, failed, no_improve = await self.process_test_results(
            test_results, tm, base_cov
        )

        return improved, failed, no_improve

    # questionable decision to make non-existent func Functions ..
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
        """
        Takes the results from run_test and processes it into a list of
        coverage enhancing test cases and failed tests
        """
        improved_tests: List[Tuple[Function, TestCoverage]] = []
        failed_tests: List[Tuple[Function, TestError]] = []
        noimprov_tests: List[Function] = []

        for cov_res, cov_diff, test_file in test_results:
            if cov_diff:
                new_funcs = self.get_new_funcs(test_file, tm.path)
                # 1. create args for each runner thread
                runner_args = {}
                for func in new_funcs:
                    test_error = cov_res.get_failed(func.name)
                    if test_error:
                        testgen_logger.info(f"[FAILED] Generated Func: {func.name}")
                        testgen_logger.info(f"Code: {func.to_code()}")

                        failed_tests.append((func, test_error))
                        continue

                    # TODO: make sure that this works for filename TMs as well
                    og_testfile = self.src_repo.find_file(tm.path).clone()
                    og_testfile.append(
                        func.to_code(), class_name=func.scope.name if func.scope else ""
                    )

                    patch_file = PatchFile(path=tm.path, patch=og_testfile.to_code())
                    runner_args[func] = {"patch_file": patch_file}

                # 2. run tests in parallel
                results = []
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = [
                        (func, executor.submit(self.runner.run_test, **args))
                        for func, args in runner_args.items()
                    ]
                    testgen_logger.info(
                        f"{len(futures)} tests submitted for evaluation"
                    )
                    for func, future in futures:
                        results.append((func, future.result()))

                # 3. loop through test_results and update
                for func, res in results:
                    indvtest_cov, *_ = res

                    indv_improve = indvtest_cov.coverage - del_cov.coverage
                    if indv_improve.total_cov.covered > 0:
                        testgen_logger.info(f"[IMPROVE] Generated Func: {func.name}")
                        testgen_logger.info(f"Code: {func.to_code()}")

                        improved_tests.append((func, indv_improve))
                    else:
                        testgen_logger.info(f"[NOIMPROVE] Generated Func: {func.name}")
                        testgen_logger.info(f"Code: {func.to_code()}")

                        noimprov_tests.append((func, TestCoverage([])))

                # MOVE into post analysis
                # log improvements or something
                # tgt_file = tm.targeted_files(base_path=False)[0]
                # tgt_file_after = cov_res.coverage.get_file_cov(tgt_file)
                # if tgt_file_after:
                #     logger.info(
                #         f"Target file improvement: {tgt_file_after.covered if tgt_file_after else 0}/{tgt_cov}"
                #     )
                # logger.info(
                #     f"Improvement: {cov_res.coverage.total_cov.covered}/{total_cov}"
                # )

        return improved_tests, failed_tests, noimprov_tests
