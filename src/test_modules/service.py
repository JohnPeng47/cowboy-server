# from .models import TestModule

from src.task_queue.core import TaskQueue
from src.repo.models import RepoConfig
from src.repo_ctxt import RepoTestContext
from src.auth.models import CowboyUser
from src.runner.service import run_test

from typing import List


async def get_tgt_coverage(
    *,
    task_queue: TaskQueue,
    curr_user: CowboyUser,
    repo_config: RepoConfig,
    tm_names: List[str]
):
    """Generates a target coverage for a test module."""

    repo_ctxt = RepoTestContext(repo_config)
    base_cov = await run_test(curr_user.id, repo_config.repo_name, task_queue)

    # tms = get_tm_target_coverage(repo_ctxt, test_modules, base_cov)
