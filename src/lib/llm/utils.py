import re
from typing import Tuple, List

from dataclasses import dataclass


@dataclass
class LMModelSpec:
    model: str
    cost: float
    ctxt_window: int


def extract_yaml_code(llm_output: str) -> str:
    try:
        return re.search(r"```yaml\n(.*)```", llm_output, re.DOTALL).group(1)
    except AttributeError:
        return llm_output


def extract_python_code(llm_output: str) -> str:
    try:
        return re.search(r"```python\n(.*)```", llm_output, re.DOTALL).group(1)
    except AttributeError:
        return llm_output


def extract_json_code(llm_output: str) -> str:
    try:
        return re.search(r"```json\n(.*)```", llm_output, re.DOTALL).group(1)
    except AttributeError:
        return llm_output


def extract_test_functions(llm_output: str) -> List[str]:
    PYTHON_FUN_DEF = r"\+?\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\("

    return re.findall(PYTHON_FUN_DEF, llm_output)
