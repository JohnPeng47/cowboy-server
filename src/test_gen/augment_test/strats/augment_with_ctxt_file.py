from .augment_base import AugmentTestStrategy
from .prompt import AugmentTestPromptWithCtxt
from ..types import CtxtWindowExceeded
from ..utils import gen_enumerated_code_str, get_current_git_commit

from typing import TYPE_CHECKING

from logging import getLogger

if TYPE_CHECKING:
    from cowboy_lib.test_modules import TestModule


logger = getLogger("test_results")


class AugmentClassWithCtxtStrat(AugmentTestStrategy):
    """
    Augment the test with a chunk of code
    """

    def build_prompt(self) -> AugmentTestPromptWithCtxt:
        prompt = AugmentTestPromptWithCtxt()

        curr_commit = get_current_git_commit(self.src_repo.repo_path)
        test_code = self.test_module.get_test_code(curr_commit)

        # test_file = self.repo_ctxt.src_repo.get_file(self.test_module.test_file.path)
        # test_code = self.get_test_code(test_file, self.test_module.nodes)
        # test_code = gen_enumerated_code_str(test_code)

        logger.info(f"ADDITIVE TEST CODE: {test_code}")

        test_fit = prompt.insert_line("test_code", test_code)
        if not test_fit:
            raise CtxtWindowExceeded("Test code too large to fit in prompt")

        for fp in self.test_module.targeted_files():
            print("Inserting file context: ", fp)
            file = self.src_repo.get_file(fp)
            code_fit = prompt.insert_line("file_contents", file.to_code())
            if not code_fit:
                logger.warn(f"File {fp} too large to fit in prompt")
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
                logger.error(f"Error: {e}")
                continue

        return test_code
