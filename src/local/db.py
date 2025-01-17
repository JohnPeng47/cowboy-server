import os
import json
from typing import Dict, List, Optional
from src.repo.models import RepoConfig
from src.runner.local.run_test import get_repo_config 
from src.config import EVAL_DATA_ROOT
from src.lib.test_modules import TestModule

# Pseudo DB:
# Ensures that all calls to persisted data models goes through this file

# Note:
# Have to store TestModule separately because it exceeds what Braintrust is willing to store
# per dataset input

class DatasetCreationError(Exception):
    pass

# NEWTODO: the functions here probably should be implemented with a db instead
####################################################################################################
def get_tm(repo_name: str, tm_name: str) -> Optional[TestModule]:
    """
    Read TM from file
    """
    tm_dir = EVAL_DATA_ROOT / repo_name / "tms"
    os.makedirs(tm_dir, exist_ok=True)

    tm_file = tm_dir / f"{tm_name}.json"
    try:
        with open(tm_file, "r") as f:
            return TestModule.from_json(json.loads(f.read()))
    except FileNotFoundError:
        raise DatasetCreationError(f"{tm_name} was not found. Consider rerunning setup_repo/setup_handicap to recreate the data")

def persist_tm(repo_name: str, tm: TestModule):
    """
    Persist both the TM and the row to disk
    """
    tm_dir = EVAL_DATA_ROOT / repo_name / "tms"
    tm_dir.mkdir(exist_ok=True)

    # Write the test module
    tm_file = tm_dir / f"{tm.name}.json"
    with open(tm_file, "w") as f:
        json.dump(tm.to_json(), f, indent=2)

def get_repo(repo_name: str, ret_json = False) -> RepoConfig:
    return get_repo_config(repo_name, ret_json = ret_json)
####################################################################################################