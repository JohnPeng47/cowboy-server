from dataclasses import dataclass
from collections import defaultdict
from jinja2 import Template

from typing import List, NamedTuple
import tiktoken

from enum import Enum, auto


class StratResult(NamedTuple):
    contents: str
    test_path: str


class StrategyInitError(Exception):
    pass


class StrategyMode(Enum):
    GEN_NEW_TEST = auto()
    AUGMENT_TEST = auto()


@dataclass
class LMModelSpec:
    model: str
    cost: float
    ctxt_window: int


class CtxtWindowExceeded(Exception):
    pass


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


class Prompt:
    def __init__(self, prompt: str, model_spec: LMModelSpec, keywords: List[str]):
        self._prompt = prompt
        self._keyword_dict = defaultdict(lambda: "")
        self._keywords = keywords
        self._max_len = model_spec.ctxt_window
        self._model_name = model_spec.model
        self._current_len = self._tokenize(prompt)

    def _tokenize(self, prompt: str):
        # Fails with: ValueError: Unknown encoding <Encoding 'cl100k_base'>
        # encoding = tiktoken.encoding_for_model(self._model_name)
        return num_tokens_from_string(prompt, "cl100k_base")

    def insert_line(self, keyword: str, line: str, preamble: str = "") -> bool:
        if keyword not in self._keywords:
            raise ValueError(f"Keyword {keyword} not found in prompt")

        str_len = self._tokenize(line)
        if self._current_len + str_len > self._max_len:
            return False
        else:
            self._keyword_dict[keyword] += preamble + "\n" + line + "\n"

        return True

    def get_prompt(self) -> str:
        template = Template(self._prompt)
        return template.render(**self._keyword_dict)
