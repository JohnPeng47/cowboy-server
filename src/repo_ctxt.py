from lib.repo.source_repo import SourceRepo
from lib.repo.repository import GitRepo

from pathlib import Path
import uuid

from src.repo.models import RepoConfig

import os
from git import Repo

from pathlib import Path
import shutil

from src.config import REPOS_ROOT
from src.utils import gen_random_name

from src.repo.models import RepoConfig


def del_file(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    import stat

    # Is the error an access error?
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


def create_repo(repo_conf: RepoConfig) -> RepoConfig:
    """
    Forks the URL and clones the repo
    """
    if not repo_conf.source_folder:
        # forked_url = fork_repo(repo_conf.url)
        # TODO: troubleshoot this later
        forked_url = ""
        cloned_path = clone_repo(repo_conf)

    return forked_url, str(cloned_path)


def clone_repo(repo_conf: RepoConfig) -> Path:
    """
    Creates a clone of the repo locally
    """
    dest_folder = Path(REPOS_ROOT) / repo_conf.repo_name / gen_random_name()
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)  # Ensure the destination folder exists

    # Repo.clone_from(repo_conf.forked_url, dest_folder)
    Repo.clone_from(repo_conf.url, dest_folder)
    return dest_folder


def delete_repo(repo_name: str):
    """
    Deletes a repo from the db and all its cloned folders
    """
    repo_path = Path(REPOS_ROOT) / repo_name
    shutil.rmtree(repo_path, onerror=del_file)


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
        self.git_repo = GitRepo(self.repo_path)
        self.src_repo = SourceRepo(self.repo_path)

        # self.run_config.interp = r"C:\Users\jpeng\Documents\business\auto_test\src\config\fastapi-users\fastapi-users-test\Scripts\python.exe"
        # self.runner = PytestDiffRunner(
        #     self.run_config, cache_db=cache_db, cloned_dirs=cloned_dirs
        # )
