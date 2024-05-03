from pydantic import BaseModel


class AugmentTestRequest(BaseModel):
    tm_name: str
    repo_name: str
