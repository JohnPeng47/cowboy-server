from src.lib.repo.repository import PatchFileContext, GitRepo
from src.lib.coverage import CoverageResult
from src.lib.api.runner.shared import RunTestTaskArgs, FunctionArg

from pydantic import BaseModel, validator
from typing import List, Optional


class PythonConf(BaseModel):
    cov_folders: List[str]
    interp: str
    test_folder: Optional[str]
    pythonpath: Optional[str]

    # @validator("interp")
    # def validate_interp(cls, v):
    #     import os

    #     if not os.path.exists(v):
    #         raise ValueError(f"Interpreter path {v} does not exist")
    #     return v


class RepoConfig(BaseModel):
    repo_name: str  # of form owner_repo
    url: str
    cloned_folders: List[str]  # list of cloned folders used for parallelizing run_test
    source_folder: str  # ???
    # pytest specific confs (although they could be generally applicable)
    python_conf: "PythonConf"
    is_experiment: Optional[bool] = False

    @validator("url")
    def validate_url(cls, v):
        import re

        if not re.match(r"^https:\/\/github\.com\/[\w-]+\/[\w-]+(\.git)?$", v):
            raise ValueError(
                "URL must be a valid GitHub HTTPS URL and may end with .git"
            )
        # if v.endswith(".git"):
        #     raise ValueError("URL should not end with .git")
        if re.match(r"^git@github\.com:[\w-]+\/[\w-]+\.git$", v):
            raise ValueError("SSH URL format is not allowed")
        return v

    def __post_init__(self):
        if isinstance(self.python_conf, dict):
            self.python_conf = PythonConf(**self.python_conf)

    def serialize(self):
        return {
            "repo_name": self.repo_name,
            "url": self.url,
            "cloned_folders": self.cloned_folders,
            "source_folder": self.source_folder,
            "python_conf": self.python_conf.__dict__,
            "is_experiment": self.is_experiment,
        }
