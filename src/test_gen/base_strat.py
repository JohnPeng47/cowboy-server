from cowboy_lib.repo.source_repo import SourceRepo

from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass

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
