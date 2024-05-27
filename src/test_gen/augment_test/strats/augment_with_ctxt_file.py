from .augment_base import AugmentTestStrategy
from .prompt import AugmentTestPromptWithCtxt
from ..types import CtxtWindowExceeded
from ..utils import get_current_git_commit

from typing import TYPE_CHECKING

from src.logger import testgen_logger


class AugmentClassWithCtxtStrat(AugmentTestStrategy):
    """
    Provides the src code context from the source code file targeted by the
    test_module
    """

    def build_prompt(self) -> AugmentTestPromptWithCtxt:
        prompt = AugmentTestPromptWithCtxt()
        curr_commit = get_current_git_commit(self.src_repo.repo_path)

        test_code = self.test_module.get_test_code(curr_commit)
        test_fit = prompt.insert_line("test_code", test_code)
        if not test_fit:
            raise CtxtWindowExceeded("Test code too large to fit in prompt")

        # TODO: how to narrow the scope of this to class or even function
        # have ref to func/class node in TargetCode
        for fp in self.test_module.targeted_files():
            testgen_logger.info(f"Src file ctxt of {self.test_module.name}: {fp}")
            file = self.src_repo.find_file(fp)
            code_fit = prompt.insert_line("file_contents", file.to_code())

            if not code_fit:
                testgen_logger.warn(f"File {fp} too large to fit in prompt")
                continue

        return prompt.get_prompt()

    def get_test_code(self, test_file, nodes):
        test_code = ""
        for node in nodes:
            try:
                test_code += test_file.find_by_nodetype(
                    node.name, node_type=node.node_type
                ).to_code()
            except Exception as e:
                testgen_logger.error(f"Error: {e}")
                continue

        return test_code
