from ...base_strat import BaseStrategy

from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from cowboy_lib.test_modules import TestModule

from logging import getLogger

logger = getLogger("test_results")


@dataclass
class LLMResAppend:
    start: int
    lines: List[str]

    def __post_init__(self):
        self.start = int(self.start)

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

        self.test_file = self.src_repo.get_file(
            self.test_module.test_file.path,
        )
        # this is weird .. we should just make it an arg on BaseStrategy
        self.target_cov = kwargs.get("target_cov", None)
        self.failed_index = 0

    def parse_llm_res(self, llm_res: str) -> str:
        lines = llm_res.split("\n")
        llm_out = LLMResAppend(int(lines[0]), lines[1:])

        logger.debug(f"Generated code: \n{llm_out.__repr__()}")

        new_test_file = self.test_module.test_file.clone()
        new_test_file.append(
            "\n".join(llm_out.lines),
            class_name=self.test_module.name if self.test_module._isclass else "",
        )

        return new_test_file.to_code()
