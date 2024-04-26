from lib.repo.source_repo import SourceRepo
from lib.repo.repository import GitRepo

from pathlib import Path
import uuid

from src.repo.models import RepoConfig


# TODO: make this into factory constructor
# so we dont have to import all this shit
class RepoTestContext:
    def __init__(
        self,
        repo_conf: RepoConfig,
    ):
        # experiment id for tracking different runs
        self.exp_id = str(uuid.uuid4())[:8]

        self.repo_path = Path(repo_conf.source_folder)
        self.git_repo = GitRepo(repo_conf.source_folder)
        self.src_repo = SourceRepo(repo_conf.source_folder)

        # self.run_config.interp = r"C:\Users\jpeng\Documents\business\auto_test\src\config\fastapi-users\fastapi-users-test\Scripts\python.exe"
        # self.runner = PytestDiffRunner(
        #     self.run_config, cache_db=cache_db, cloned_dirs=cloned_dirs
        # )
