from .models import TestModule
from lib.baseline import get_tm_target_coverage

from src.repo.models import RepoConfig
from src.repo.repo_ctxt import RepoTestContext
from src.auth.models import CowboyUser

from typing import List


def get_tgt_coverage(
    *,
    db_session,
    curr_user: CowboyUser,
    repo_config: RepoConfig,
    test_modules: List[TestModule]
) -> RepoConfig:
    """Generates a target coverage for a test module."""

    repo_ctxt = RepoTestContext(repo_config)
    base_cov = repo_ctxt.runner.run_test()

    tms = get_tm_target_coverage()
