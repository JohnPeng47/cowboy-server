from src.lib.repo.source_repo import SourceRepo

from abc import ABC, abstractmethoda
from pathlib import Path
from dataclasses import dataclass

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .strats.prompt import Prompt
    

from src.runner.service import RunServiceArgs


@dataclass
class TestCaseInput(ABC):

    @property
    @abstractmethod
    def path(self) -> Path:
        raise NotImplementedError


class BaseStrategy(ABC):
    def __init__(self, src_repo: SourceRepo, test_input: TestCaseInput):
        self.src_repo = src_repo
        self.test_input = test_input
        self.prompt: "Prompt" = None

    @abstractmethod
    def build_prompt(self) -> str:
        """
        Builds the base prompt according to the strategy
        """

        raise NotImplementedError

    @abstractmethod
    def parse_llm_res(self):
        """
        Parses the LLM response to get the generated code
        """
        raise NotImplementedError

    def update_prompt(self) -> str:
        """
        Updates the prompt with the generated code
        """
        return self.build_prompt()