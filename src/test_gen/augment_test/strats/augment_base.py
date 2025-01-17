from ..base_strat import BaseStrategy

from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.lib.test_modules import TestModule

from logging import getLogger

logger = getLogger("test_results")


@dataclass
class LLMResAppend:
    lines: List[str]

    def __repr__(self):
        return "\n".join(self.lines)


class AugmentTestStrategy(BaseStrategy):
    """
    Generates a test case for a test module
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # "cast" TestCaseInput to TestModule
        self.test_module: "TestModule" = self.test_input

        self.test_file = self.src_repo.find_file(
            self.test_module.test_file.path,
        )
        # this is weird .. we should just make it an arg on BaseStrategy
        self.target_cov = kwargs.get("target_cov", None)
        self.failed_index = 0

    def parse_llm_res(self, llm_res: str) -> str:
        lines = llm_res.split("\n")
        llm_out = LLMResAppend(lines=lines)

        new_test_file = self.test_module.test_file.clone()
        new_test_file.append(
            "\n".join(llm_out.lines),
            class_name=self.test_module.name if self.test_module._isclass else "",
        )

        return new_test_file.to_code()
