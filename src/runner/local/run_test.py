from src.lib.repo.repository import PatchFile
# TODO: need to replace definition of RunTestTaskArgs to be compatible with include_tests == TestModule
# from src.lib.api.runner.shared import RunTestTaskArgs
from src.lib.coverage import CoverageResult
from src.lib.ast.code import Function
from src.lib.test_modules import TestModule

from ..models import RunServiceArgs 
from .python import PytestDiffRunner
from .models import RepoConfig
from .cache import cache_test_run

from pydantic import BaseModel
from src.config import TESTCONFIG_ROOT
from pathlib import Path
from typing import List, Tuple, Optional, Any
import json

class RunTestTaskArgs(BaseModel):
    repo_name: str
    patch_file: Optional[PatchFile] = None
    exclude_tests: List[Tuple[Any, Any]] = []
    include_tests: Optional[TestModule] = None

    model_config = {"arbitrary_types_allowed": True}

class RepoConfigException(Exception):
    pass

def get_repo_config(repo_name: str, ret_json = False) -> RepoConfig:
    filename = f"{repo_name}.json"
    with open(TESTCONFIG_ROOT / filename, "r") as f:
        if ret_json:
            return json.load(f)
        
        config = RepoConfig(**json.load(f))
        if config.repo_name != repo_name:
            raise RepoConfigException(f"Config.repo_name must be the same as the filename {filename}")
    
        return config

@cache_test_run
async def run_test(
    repo_name: str,
    service_args: RunServiceArgs, # dont actually need this argument here, just for compatability
    exclude_tests: List[Tuple[Function, str]] = [],
    include_tests: TestModule = None,
    patch_file: PatchFile = None,
    stream: bool = False,
    use_cache: bool = True,
    delete_last: bool = False
) -> CoverageResult:
    repo_config = get_repo_config(repo_name)
    args = RunTestTaskArgs(
        repo_name=repo_name,
        patch_file=patch_file,
        exclude_tests=exclude_tests,
        include_tests=include_tests,
    )
    runner = PytestDiffRunner(repo_config)
    cov, _, _ = runner.run_testsuite(args, stream=stream)

    return cov