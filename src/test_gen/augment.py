from cowboy_lib.repo import SourceRepo, GitRepo

from .augment_test.composer import Composer
from .models import AugmentTestResult

from src.auth.models import CowboyUser
from src.auth.service import retrieve_oai_key
from src.runner.service import RunServiceArgs
from src.runner.service import run_test
from src.queue.core import TaskQueue
from src.repo.models import RepoConfig
from src.test_modules.models import TestModuleModel

from .service import create_test_result

from sqlalchemy.orm import Session
from pathlib import Path
from typing import List


# FEATURE: add lines additional lines covered here
def commit_message(test_names: List[str], cov_plus: int):
    names_str = "\n".join(test_names)
    return "Added test cases: \n" + names_str


async def augment_test(
    *,
    db_session: Session,
    task_queue: TaskQueue,
    repo: RepoConfig,
    tm_model: TestModuleModel,
    curr_user: CowboyUser,
) -> List[AugmentTestResult]:
    """
    Generate test cases for the given test module using the specified strategy and evaluator
    """
    src_repo = SourceRepo(Path(repo.source_folder))
    git_repo = GitRepo(Path(repo.source_folder), remote=repo.remote, main=repo.main)
    tm = tm_model.serialize(src_repo)
    run_args = RunServiceArgs(
        user_id=curr_user.id, repo_name=repo.repo_name, task_queue=task_queue
    )

    base_cov = await run_test(run_args)
    composer = Composer(
        strat="WITH_CTXT",
        evaluator="ADDITIVE",
        src_repo=src_repo,
        test_input=tm,
        run_args=run_args,
        base_cov=base_cov,
        api_key=retrieve_oai_key(curr_user.id),
    )

    improved_tests, failed_tests, no_improve_tests = await composer.generate_test(
        n_times=1
    )

    # write all improved test to source file and check out merge on repo
    # serialize tm first
    test_results = []
    test_file = tm.test_file
    for improved, cov in improved_tests:
        print("Improved test: ", improved.name)
        test_result = create_test_result(
            db_session=db_session,
            repo_id=repo.id,
            name=improved.name,
            test_case=improved.to_code(),
            cov_list=cov.cov_list,
            tm_id=tm_model.id,
            commit_hash=git_repo.get_curr_commit(),
            testfile=str(test_file.path),
            classname=None,
        )
        test_results.append(test_result)

    return test_results
