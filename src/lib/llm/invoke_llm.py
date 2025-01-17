from typing import List, Tuple
import asyncio

from .models import BaseModel

from .utils import (
    # TurboModel,
    extract_python_code,
    extract_yaml_code,
    extract_json_code,
)


async def invoke_llm_async(
    prompt: str,
    model: BaseModel,
    n_times: int,
    output: str = "str",
) -> List[str]:
    output = []

    coroutines = []
    for _ in range(n_times):
        coroutines.append(model.query(prompt))

    llm_outputs = await asyncio.gather(*coroutines)

    # should add the other methods here
    for out in llm_outputs:
        if output == "yaml":
            out = extract_yaml_code(out)
        elif output == "json":
            out = extract_json_code(out)
        elif output == "code":
            out = extract_python_code(out)

    return llm_outputs
