from cowboy_lib.repo.repository import GitRepo
from cowboy_lib.repo.diff import DiffMode

from src.queue.core import TaskQueue
from src.auth.service import get_user_token
from src.repo.service import get_all, get_or_raise
from src.test_modules.service import get_all_tms
from src.test_modules.models import TestModuleModel
from src.config import API_ENDPOINT

from src.logger import sync_repo as log

from pathlib import Path
import asyncio
from sqlalchemy.orm import Session
from typing import List
import threading
import requests
from urllib.parse import urljoin


class APIClient:
    def __init__(self, endpoint, token):
        self.server = endpoint
        self.headers = {"Authorization": f"Bearer {token}"}

    async def get(self, uri: str):
        url = urljoin(self.server, uri)
        res = requests.get(url, headers=self.headers)

        return res.json()

    async def post(self, uri: str, data: dict):
        url = urljoin(self.server, uri)
        res = requests.post(url, json=data, headers=self.headers)

        return res.json()

    async def build_mapping(self, repo_name, mode, tms):
        """
        Builds the test module to source file mapping for each selected
        test module
        """
        await self.post(
            "/tm/build-mapping",
            {
                "repo_name": repo_name,
                "mode": mode,
                "tms": tms,
                "files": [],
                # TODO: change this to False
                "overwrite": True,
            },
        )


async def check_for_changed_files(
    db_session: Session, task_queue: TaskQueue
) -> ChangedFiles:
    """
    Checks for repo update
    """
    while True:
        repos = get_all(db_session=db_session)
        for repo in repos:
            git_repo = GitRepo(Path(repo.source_folder))
            user_token = get_user_token(db_session=db_session, user_id=repo.user_id)
            api_client = APIClient(API_ENDPOINT, user_token)

            commit = git_repo.diff_remote()
            if commit:
                for diff in commit.diffs:
                    if diff.attrs.mode == DiffMode.MODIFIED:
                        modified_file = diff.attrs.a_path
                        impacted_tm = (
                            testfile_to_tm(db_session, repo.id, modified_file)
                            if is_test_file(modified_file)
                            else srcfile_to_tm(db_session, repo.id, modified_file)
                        )
                        log.info(f"Impacted tm: {impacted_tm.name}")

                        if not impacted_tm:
                            # TODO: really bad, because it implies that we are
                            # missing some kind of update to the repo
                            continue

                        await api_client.build_mapping(
                            repo.repo_name, "module", [impacted_tm.name]
                        )
                    # TODO: do something for this
                    elif diff.attrs.mode == DiffMode.NEW:
                        continue

        await asyncio.sleep(10)
