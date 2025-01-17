from .base_strat import BaseStrategy, TestCaseInput
from .types import StratResult
from .evaluators import (
    Evaluator,
    AugmentAdditiveEvaluator,
    AugmentParallelEvaluator,
    EvaluatorType,
    AUGMENT_EVALS,
)
from src.lib.repo.repository import PatchFile
from src.lib.repo.source_repo import SourceRepo
from src.lib.repo.source_file import TestFile, Function, LintException
from src.lib.coverage import TestCoverage, TestError

from src.test_gen.augment_test.strats import AugmentStratType, AUGMENT_STRATS
from src.runner.service import RunServiceArgs
from src.exceptions import CowboyRunTimeException
from src.llm import LLMModel
from src.logger import testgen_logger as log
from src.utils import green_text

from src.config import LLM_RETRIES

import re
from dataclasses import dataclass
from typing import Tuple, List, Callable


def extract_python_code(llm_output: str) -> str:
    try:
        return re.search(r"```python\n(.*)```", llm_output, re.DOTALL).group(1)
    except AttributeError:
        return llm_output

@dataclass
class TestAugmentArgs:
    strat: AugmentStratType
    n_times: int
    evaluator: EvaluatorType
    model_name: str

class Composer:
    """s
    Used to instantiate different combinations of strategies for generating test cases
    """

    def __init__(
        self,
        repo_name: str,
        strat: AugmentStratType,
        evaluator: EvaluatorType,
        src_repo: SourceRepo,
        test_input: TestCaseInput,
        run_args: RunServiceArgs,
        model: str,
        api_key: str = None,
        verify: bool = False,
        run_test: Callable = None,
        use_cache: bool = True,
        delete_last: bool = False
    ):
        self.repo_name = repo_name
        self.src_repo = src_repo
        self.test_input = test_input
        self.verify = verify
        self.run_args = run_args
        self.run_test = run_test
        # cache settings
        self.use_cache = use_cache
        self.delete_last = delete_last

        self.strat: BaseStrategy = AUGMENT_STRATS[strat](self.src_repo, self.test_input)
        self.evaluator: Evaluator = AUGMENT_EVALS[evaluator](
            self.repo_name, 
            self.src_repo, 
            self.run_args, 
            test_input, 
            self.run_test,
            use_cache = self.use_cache,
            delete_last = self.delete_last
        )
        self.model_name = model
        self.model = LLMModel()

        if self.use_cache:
            print(green_text(f"RUNNING WITH CACHE: use_cache = {self.use_cache}, delete_last = {self.delete_last}"))

    def get_strat_name(self) -> str:
        return self.__class__.__name__

    def filter_overlap_improvements(
        self, 
        tests: List[Tuple[Function, TestCoverage]], 
        module_cov: TestCoverage
    ) -> List[Tuple[Function, TestCoverage]]:
        no_overlap = []
        overlap_cov = module_cov
        for test, cov in tests:
            new_cov = overlap_cov + cov
            if new_cov.total_cov.covered > overlap_cov.total_cov.covered:
                no_overlap.append((test, cov))
                overlap_cov = new_cov

        return no_overlap

    # TODO: this function name is a lie, we should parallelize this
    # async def gen_test_parallel(self, n_times: int) -> Tuple[
    #     List[Tuple[Function, TestCoverage]],
    #     List[Tuple[Function, TestError]],
    #     List[Function],
    # ]:
    #     improved_tests = []
    #     failed_tests = []
    #     no_improve_tests = []

    #     prompt = self.strat.build_prompt()
    #     print(f"Prompt: {prompt}")

    #     model_res = await invoke_llm_async(prompt, self.model, n_times)
    #     llm_results = [self.strat.parse_llm_res(res) for res in model_res]
    #     test_results = [StratResult(res, self.test_input.path) for res in llm_results]
    #     improved, failed, no_improve = await self.evaluator(
    #         test_results,
    #         self.test_input,
    #         self.base_cov,
    #         n_times=n_times,
    #     )

    #     improved_tests.extend(improved)
    #     filtered_improved = self.filter_overlap_improvements(improved_tests)
    #     improved_tests = filtered_improved

    #     failed_tests.extend(failed)
    #     no_improve_tests.extend(no_improve)

    #     return improved_tests, failed_tests, no_improve_tests

    async def gen_test_serial_additive(self, n_times: int) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:
        if not isinstance(self.evaluator, AugmentAdditiveEvaluator):
            raise Exception(
                f"Expected AugmentAdditiveEvaluator, got {self.evaluator.__class__}"
            )
        
        log.info(f"### Starting serial additive test for {self.test_input.name} ###")

        improved_tests = []
        failed_tests = []
        no_improve_tests = []
        prompt = self.strat.build_prompt()

        log.info(f"Prompt: \n{prompt}")

        updated_patchfile = None
        for i in range(n_times):
            src_file = await self._llm_generate_with_retry(prompt, i)

            # need to update the contents of tesst_file to account for new tests that
            # have been generated
            module_cov = await self.run_test(
                self.repo_name, 
                self.run_args, 
                include_tests=self.test_input,
                patch_file=updated_patchfile,
                use_cache=self.use_cache,
                delete_last=self.delete_last
            )

            module_cov = module_cov.get_coverage()
            test_result = [StratResult(src_file, self.test_input.path)]
            improved, failed, no_improve = await self.evaluator(
                test_result,
                self.test_input,
                module_cov,
                self.test_input.test_file,
                n_times=n_times,
            )
            improved_tests.extend(improved)
            filtered_improved = self.filter_overlap_improvements(improved_tests, module_cov)
            improved_tests = filtered_improved

            log.info(f"Filtered out: {len(improved) - len(filtered_improved)} tests")
            log.info(f"Round [{i + 1}/{n_times}] => Improved: {len(improved)}, Failed: {len(failed)}, NoImprove: {len(no_improve)}")

            # update test input with new functions that improved coverage
            for new_func in [
                func
                for func, _ in improved
                if func in [f[0] for f in filtered_improved]
            ]:
                self.test_input.test_file.append(
                    # NEWTODO(BUG1): ideally we should have to lstrip here
                    new_func.to_code().lstrip(),
                    # wrong too, we need to check the
                    class_name=new_func.scope.name if new_func.scope else "",
                )

            failed_tests.extend(failed)
            no_improve_tests.extend(no_improve)
            updated_patchfile = PatchFile(
                path=self.test_input.path,
                patch=self.test_input.test_file.to_code(),
            )
            prompt = self.strat.update_prompt(self.test_input.test_file.to_code())
            
        return improved_tests, failed_tests, no_improve_tests

    async def generate_test(self, n_times: int) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:
        if isinstance(self.evaluator, AugmentAdditiveEvaluator):
            return await self.gen_test_serial_additive(n_times)
        
        # doesnt work rn ...
        # elif isinstance(self.evaluator, AugmentParallelEvaluator):
        #     return await self.gen_test_parallel(n_times)

    async def _llm_generate_with_retry(self, prompt: str, i) -> str:
        """
        Retry LLM generation with specified number of retries.
        Returns the parsed source file or raises CowboyRunTimeException.
        """
        retries = LLM_RETRIES
        src_file = None
        
        while retries > 0 and not src_file:
            try:
                llm_res = self.model.invoke(
                    prompt,
                    model_name = self.model_name,
                    key=i,
                    use_cache = self.use_cache,
                    delete_cache = self.delete_last,
                )
                # need this for deepseek ..
                llm_res = extract_python_code(llm_res)

                src_file = self.strat.parse_llm_res(llm_res)
            except (SyntaxError, ValueError, LintException):
                log.info(f"LLM syntax error ... {retries} left")
                retries -= 1
                continue

        if not src_file:
            raise CowboyRunTimeException(
                f"LLM generation failed for {self.test_input}"
            )
        
        return src_file
