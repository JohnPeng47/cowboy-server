# from .models import TestModule
from src.longterm_tasks import get_tm_target_coverage
from src.task_queue.core import TaskQueue
from src.repo.models import RepoConfig
from src.repo_ctxt import RepoTestContext
from src.auth.models import CowboyUser
from src.runner.service import run_test

from .iter_tms import iter_test_modules

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

    test_modules = iter_test_modules(repo_ctxt.src_repo)
    if tm_names:
        test_modules = filter(lambda tm: tm.name in tm_names, test_modules)

    for tm in test_modules:
        print("Baselining tm: ", tm.name)
        # these enriched tms have test to source file mappings
        enriched_tm = await get_tm_target_coverage(
            repo_ctxt, tm, base_cov, curr_user.id, repo_config.repo_name, task_queue
        )

        # write to db
        # enriched_tm.save()

    print("FINISHED RUNNING")
