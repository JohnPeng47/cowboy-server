from .augment_base import AugmentTestStrategy
from .prompt import AugmentTestPrompt
from ...utils import gen_enumerated_code_str, get_current_git_commit


from logging import getLogger


logger = getLogger("test_results")


class AugmentClassStrat(AugmentTestStrategy):
    """
    Just simply executes the LLM prompt without providing additional
    context
    """

    def build_prompt(self) -> str:
        curr_commit = get_current_git_commit(self.src_repo.repo_path)

        prompt = AugmentTestPrompt()

        test_code = self.test_module.get_test_code(curr_commit)
        # test_file = self.repo_ctxt.src_repo.get_file(self.test_module.test_file.path)
        # test_code = self.get_test_code(test_file, self.test_module.nodes)

        logger.info(f"ADDITIVE TEST CODE: {test_code}")

        test_code = gen_enumerated_code_str(test_code.split("\n"))
        prompt.insert_line("test_code", test_code)

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
