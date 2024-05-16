from .base_strat import BaseStrategy

from src.llm.invoke_llm import invoke_llm_async

from .base_strat import TestCaseInput
from .types import StratResult

from .evaluators import (
    Evaluator,
    AugmentAdditiveEvaluator,
    AugmentParallelEvaluator,
    EvaluatorType,
    AUGMENT_EVALS,
)

from src.test_gen.augment_test.strats import AugmentStratType, AUGMENT_STRATS

from cowboy_lib.repo.source_repo import SourceRepo
from cowboy_lib.repo.source_file import Function
from cowboy_lib.coverage import TestCoverage, TestError
from src.llm.models import OpenAIModel, ModelArguments

from src.runner.service import run_test, RunServiceArgs
from src.exceptions import CowboyRunTimeException

from typing import Tuple, List

from src.config import LLM_RETRIES

from logging import getLogger

logger = getLogger("test_results")
longterm_logger = getLogger("longterm")


class Composer:
    """
    Used to instantiate different combinations of strategies for generating test cases
    """

    def __init__(
        self,
        strat: AugmentStratType,
        evaluator: EvaluatorType,
        src_repo: SourceRepo,
        test_input: TestCaseInput,
        run_args: RunServiceArgs,
        # TODO: put this back in once we have Coverage persisted
        base_cov: TestCoverage,
        # target_cov: TestCoverage,
        verify: bool = False,
    ):
        self.src_repo = src_repo
        self.test_input = test_input
        self.verify = verify
        self.base_cov = base_cov
        self.run_args = run_args

        self.strat: BaseStrategy = AUGMENT_STRATS[strat](self.src_repo, self.test_input)
        self.evaluator: Evaluator = AUGMENT_EVALS[evaluator](
            self.src_repo, self.run_args
        )

        model_name = "gpt4"
        self.model = OpenAIModel(ModelArguments(model_name=model_name))

    def get_strat_name(self) -> str:
        return self.__class__.__name__

    def filter_overlap_improvements(
        self, tests: List[Tuple[Function, TestCoverage]]
    ) -> List[Tuple[Function, TestCoverage]]:
        no_overlap = []
        overlap_cov = self.base_cov.coverage
        for test, cov in tests:
            new_cov = overlap_cov + cov
            if new_cov.total_cov.covered > overlap_cov.total_cov.covered:
                no_overlap.append((test, cov))
                overlap_cov = new_cov

        return no_overlap

    # TODO: this function name is a lie, we should parallelize this
    async def gen_test_parallel(self, n_times: int) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:

        improved_tests = []
        failed_tests = []
        no_improve_tests = []

        prompt = self.strat.build_prompt()
        model_res = await invoke_llm_async(prompt, self.model, n_times)

        llm_results = [self.strat.parse_llm_res(res) for res in model_res]
        test_results = [StratResult(res, self.test_input.path) for res in llm_results]

        improved, failed, no_improve = await self.evaluator(
            test_results, self.test_input, self.base_cov, n_times=n_times
        )

        improved_tests.extend(improved)
        filtered_improved = self.filter_overlap_improvements(improved_tests)
        improved_tests = filtered_improved

        failed_tests.extend(failed)
        no_improve_tests.extend(no_improve)

        return improved_tests, failed_tests, no_improve_tests

    async def gen_test_serial_additive(self, n_times: int) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:
        print("RUnning additive serial")

        if not isinstance(self.evaluator, AugmentAdditiveEvaluator):
            raise Exception(
                f"Expected AugmentAdditiveEvaluator, got {self.evaluator.__class__}"
            )

        improved_tests = []
        failed_tests = []
        no_improve_tests = []

        for _ in range(n_times):
            retries = LLM_RETRIES
            src_file = None
            while retries > 0 and not src_file:
                try:
                    prompt = self.strat.build_prompt()
                    print("Prompt: ", prompt)
                    llm_res = await invoke_llm_async(
                        prompt,
                        model=self.model,
                        n_times=1,
                    )

                    src_file = self.strat.parse_llm_res(llm_res[0])
                except SyntaxError:
                    print(f"Retrying ... {retries} left")
                    retries -= 1
                    continue

            if not src_file:
                raise CowboyRunTimeException("LLM generation failed")

            test_result = [StratResult(src_file, self.test_input.path)]

            # continue here
            # be careful about the fs state as represented by the test module
            # and that represented by the source repo
            # although i think if we limit our modifications to the test_input
            # we should be fine
            improved, failed, no_improve = await self.evaluator(
                test_result, self.test_input, self.base_cov, n_times=n_times
            )
            improved_tests.extend(improved)
            filtered_improved = self.filter_overlap_improvements(improved_tests)
            improved_tests = filtered_improved

            # update test input with new functions that improved coverage
            for new_func in [
                func
                for func, _ in improved
                if func in [f[0] for f in filtered_improved]
            ]:
                self.test_input.test_file.append(
                    new_func.to_code(),
                    # wrong too, we need to check the
                    class_name=new_func.scope.name if new_func.scope else "",
                )

            failed_tests.extend(failed)
            no_improve_tests.extend(no_improve)

            logger.debug(f"Generated code with source file: \n{src_file}")

        return improved_tests, failed_tests, no_improve_tests

    async def generate_test(self, n_times: int) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:
        if isinstance(self.evaluator, AugmentAdditiveEvaluator):
            return await self.gen_test_serial_additive(n_times)
        elif isinstance(self.evaluator, AugmentParallelEvaluator):
            return await self.gen_test_parallel(n_times)
