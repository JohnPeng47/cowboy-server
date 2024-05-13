from cowboy_lib.repo import SourceRepo, GitRepo

from .augment_test.composer import Composer

from src.database.core import Session
from src.auth.models import CowboyUser

from src.repo.service import get as get_repo
from src.test_modules.service import get_tm_by_name
from src.runner.service import RunServiceArgs
from src.task_queue.core import TaskQueue

from src.runner.service import run_test

from pathlib import Path
from typing import List


# FEATURE: add lines additional lines covered here
def commit_message(test_names: List[str], cov_plus: int):
    names_str = "\n".join(test_names)
    return "Added test cases: \n" + names_str


async def augment_test(
    *,
    task_queue: TaskQueue,
    db_session: Session,
    curr_user: CowboyUser,
    tm_name: str,
    repo_name: str
):
    """
    Generate test cases for the given test module using the specified strategy and evaluator
    """
    repo = get_repo(db_session=db_session, curr_user=curr_user, repo_name=repo_name)
    src_repo = SourceRepo(Path(repo.source_folder))
    git_repo = GitRepo(Path(repo.source_folder))
    tm_model = get_tm_by_name(db_session=db_session, repo_id=repo.id, tm_name=tm_name)
    tm = tm_model.serialize(src_repo)
    run_args = RunServiceArgs(
        user_id=curr_user.id, repo_name=repo_name, task_queue=task_queue
    )

    base_cov = await run_test(run_args)
    composer = Composer(
        strat="WITH_CTXT",
        evaluator="ADDITIVE",
        src_repo=src_repo,
        test_input=tm,
        run_args=run_args,
        base_cov=base_cov,
    )

    improved_tests, failed_tests, no_improve_tests = await composer.generate_test(
        n_times=1
    )

    # write all improved test to source file and check out merge on repo
    # serialize tm first
    test_file = tm.test_file
    f_names = []
    f_covs = 0
    for improved, cov in improved_tests:
        try:
            # class_name = None cuz these are only functions
            test_file.append(improved.to_code(), class_name=None)
            f_names.append(improved.name)
            f_covs += cov
        except Exception as e:
            continue

    print("Final testfile: ", test_file.to_code())

    commit_msg = commit_message(f_names, f_covs)
    merge_url = git_repo.checkout_and_push(tm.name, commit_msg, [test_file.path])

    return merge_url
