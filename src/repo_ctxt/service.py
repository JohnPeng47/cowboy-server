from cowboy.src.pytest_runner import PytestDiffRunner
from cowboy.src.repo.repository import (
    GitRepo,
)
from cowboy.src.core.model.repo_config import RepoConfig, PythonConf
from cowboy.src.utils import RepoPath
from cowboy.src.repo.source_repo import SourceRepo

from logging import getLogger, config as loggerConfig
from pathlib import Path
import uuid
from typing import Optional, Tuple, List, Dict

from src.repo.service import get as get_repoconf

logger = getLogger("test_results")
longterm_logger = getLogger("longterm")

ALL_REPO_CONF = "src/config"
NUM_CLONES = 2
BASE_PATH = Path("repos")


# TODO: make this into factory constructor
# so we dont have to import all this shit
class RepoTestContext:
    def __init__(
        self,
        repo_path: Path,
        repo_name: str,
        test_config: RepoConfig,
    ):
        # experiment id for tracking different runs
        self.exp_id = str(uuid.uuid4())[:8]

        self.repo_path = RepoPath(repo_path)
        self.git_repo = GitRepo(self.repo_path)
        self.src_repo = SourceRepo(self.repo_path)
        self.repo_name = repo_name

        # self.run_config.interp = r"C:\Users\jpeng\Documents\business\auto_test\src\config\fastapi-users\fastapi-users-test\Scripts\python.exe"

        self.runner = PytestDiffRunner(
            self.run_config, cache_db=cache_db, cloned_dirs=cloned_dirs
        )


def create_repo(*, db_session, curr_user, repo_name):
    repo_conf = get_repoconf(
        db_session=db_session, curr_user=curr_user, repo_name=repo_name
    )
