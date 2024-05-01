# from .models import TestModule
from src.longterm_tasks import get_tm_target_coverage
from src.task_queue.core import TaskQueue
from src.repo.models import RepoConfig
from src.repo_ctxt import RepoTestContext
from src.auth.models import CowboyUser
from src.database.core import Session
from src.runner.service import run_test
from src.ast.service import create_node

from .models import TestModuleModel, TestModule
from .iter_tms import iter_test_modules

from typing import List


def create_all_tms(
    *, db_session: Session, repo_conf: RepoConfig, repo_ctxt: RepoTestContext
):
    """Create all test modules for a repo."""
    test_modules = iter_test_modules(repo_ctxt.src_repo)

    for tm in test_modules:
        print("Saving: ", tm.name)
        create_tm(db_session=db_session, repo_conf=repo_conf, tm=tm)


def create_tm(*, db_session: Session, repo_conf: RepoConfig, tm: TestModule):
    """Create a test module and the nodes"""
    test_module = TestModuleModel(
        testfilepath=str(tm.test_file.path),
        commit_sha=tm.commit_sha,
        repo_id=repo_conf.id,
    )

    for node in tm.nodes:
        create_node(
            db_session=db_session,
            node=node,
            repo_id=repo_conf.id,
            test_module_id=test_module.id,
        )

    db_session.add(test_module)
    db_session.commit()

    return test_module


# def update_tm(*, db_session: Session, repo_conf: RepoConfig, tm: TestModule):


#     test_module = TestModuleModel(testfilepath=tm.test_file.path, commit_sha=tm.commit_sha, repo_id=repo_conf.id)


#     db_session.add(tm)
#     db_session.commit()

#     return tm


async def get_tgt_coverage(
    *,
    db_session: Session,
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
        # these enriched tms have test to source file mappings
        enriched_tm = await get_tm_target_coverage(
            repo_ctxt, tm, base_cov, curr_user.id, repo_config.repo_name, task_queue
        )

        save_tm(db_session=db_session, repo_conf=repo_config, tm=enriched_tm)

        # write to db
        # enriched_tm.save()

    print("FINISHED RUNNING")
