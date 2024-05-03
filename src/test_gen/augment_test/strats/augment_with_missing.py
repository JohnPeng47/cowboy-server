from .augment_base import AugmentTestStrategy
from .prompt import AugmentTestPromptMiss

from ...types import CtxtWindowExceeded
from ...utils import gen_enumerated_code_str, get_current_git_commit

from logging import getLogger

logger = getLogger("test_results")


class AugmentModuleMissing(AugmentTestStrategy):
    """
    Augment test by focusing on missing/uncovered lines
    """

    def build_prompt(self) -> AugmentTestPromptMiss:
        if not self.target_cov:
            raise ValueError("Target coverage not set")

        prompt = AugmentTestPromptMiss()

        curr_commit = get_current_git_commit(self.src_repo.repo_path)
        test_code = self.test_module.get_test_code(curr_commit).split("\n")
        test_code = gen_enumerated_code_str(test_code)
        missing_lines = self.target_cov.print_lines(line_type="missing")

        logger.info(f"Missing lines: {missing_lines}")

        test_fit = prompt.insert_line("test_code", test_code)
        if not test_fit:
            raise CtxtWindowExceeded("Test code too large to fit in prompt")

        for fp in self.test_module.targeted_files():
            file = self.src_repo.get_file(fp)
            code_fit = prompt.insert_line("file_contents", file.to_code())
            if not code_fit:
                logger.warn(f"File {fp} too large to fit in prompt")
                continue

        prompt.insert_line("missing_lines", missing_lines)
        return prompt.get_prompt()
