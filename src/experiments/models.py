from pydantic import BaseModel
from typing import List


class ExperimentRequest(BaseModel):
    repo_name: str
    tms: List[str]
    to_keep: int
    to_delete: int
