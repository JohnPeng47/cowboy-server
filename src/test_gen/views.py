from cowboy_lib.repo import SourceRepo, GitRepo
from src.database.core import get_db
from src.auth.service import get_current_user
from src.queue.core import get_queue
from src.stats.service import update_repo_stats
from src.repo.service import get_or_raise, get_by_id_or_raise

from .models import (
    AugmentTestRequest,
    AugmentTestResponse,
    UserDecisionRequest,
    UserDecisionResponse,
    TestResultResponse,
)
from .augment import augment_test
from .service import (
    save_all,
    get_test_results_by_sessionid,
    get_test_result_by_id_or_raise,
)
from .service import get_session_id, select_tms
from .utils import gen_commit_msg

from sqlalchemy.orm import Session
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from functools import reduce
import asyncio

test_gen_router = APIRouter()


MODE_AUTO_ERROR_MSG = """
No test modules found for auto mode. Consider using mode=all instead, if you
do not want to specify individual test modules or files to augment 
"""

MODE_FILES_ERROR_MSG = """
No test files found for files mode. This could be because we dont have the test 
module mapping generated for {filenames}. Consider first build mapping on these
files first. If that still doesnt work, it means that we were unable to recover
the test module to source file mapping for {filenames}
"""


@test_gen_router.post("/test-gen/augment")
async def augment_test_route(
    request: AugmentTestRequest,
    db_session=Depends(get_db),
    session_id=Depends(get_session_id),
    curr_user=Depends(get_current_user),
    task_queue=Depends(get_queue),
):
    """
    Augment tests for a test module
    """
    repo = get_or_raise(
        db_session=db_session, curr_user=curr_user, repo_name=request.repo_name
    )
    src_repo = SourceRepo(Path(repo.source_folder))
    tm_models = select_tms(
        db_session=db_session, repo_id=repo.id, request=request, src_repo=src_repo
    )
    if not tm_models:
        detail = (
            MODE_AUTO_ERROR_MSG
            if request.mode == "auto"
            else MODE_FILES_ERROR_MSG.format(filenames=request.files)
        )
        return HTTPException(status_code=400, detail=detail)

    # TODO: put this into a service
    coroutines = []
    for tm_model in tm_models:
        coroutine = augment_test(
            db_session=db_session,
            task_queue=task_queue,
            repo=repo,
            tm_model=tm_model,
            curr_user=curr_user,
            session_id=session_id,
        )
        coroutines.append(coroutine)

    test_results = await asyncio.gather(*coroutines)
    test_results = reduce(lambda x, y: x + y, test_results)

    # we save here after async ops have finished running
    save_all(db_session=db_session, test_results=test_results)

    return AugmentTestResponse(session_id=session_id)


@test_gen_router.get("/test-gen/results/{session_id}")
def get_results(
    session_id: str,
    db_session: Session = Depends(get_db),
):
    trs = get_test_results_by_sessionid(db_session=db_session, session_id=session_id)
    return [
        TestResultResponse(
            id=tr.id,
            name=tr.name,
            test_case=tr.test_case,
            test_file=tr.testfile,
            cov_improved=tr.coverage_improve(),
            decided=tr.decide,
        )
        for tr in trs
    ]


@test_gen_router.post("/test-gen/results/decide/{sesssion_id}")
def accept_user_decision(
    request: UserDecisionRequest,
    curr_user=Depends(get_current_user),
    db_session=Depends(get_db),
):
    """
    Takes the result of the selected tests and appends all of the selected
    tests to TestModule (testfile/test class). Then check out a new branch against
    the remote repo with the changed files
    """

    repo_id = get_test_result_by_id_or_raise(
        db_session=db_session, test_id=request.user_decision[0].id
    ).repo_id
    repo = get_by_id_or_raise(
        db_session=db_session, curr_user=curr_user, repo_id=repo_id
    )
    src_repo = SourceRepo(Path(repo.source_folder))
    git_repo = GitRepo(Path(repo.source_folder))

    # NOTE: LintExceptions at this step should not happen because they would have occurred
    # earlier during the Evaluation phase
    changed_files = set()
    accepted_results = []
    for decision in request.user_decision:
        tr = get_test_result_by_id_or_raise(db_session=db_session, test_id=decision.id)
        test_file = src_repo.find_file(tr.testfile)
        if decision.decision:
            test_file.append(tr.test_case, class_name=tr.classname)
            src_repo.write_file(test_file.path)
            changed_files.add(str(test_file.path))
            accepted_results.append(tr)

    # update stats
    with update_repo_stats(db_session=db_session, repo=repo) as repo_stats:
        repo_stats.accepted_tests += len(accepted_results)
        repo_stats.rejected_tests += len(request.user_decision) - len(accepted_results)

    msg = gen_commit_msg(accepted_results)
    compare_url = git_repo.checkout_and_push(
        "cowboy-augmented-tests", msg, list(changed_files)
    )
    print(compare_url)

    return UserDecisionResponse(compare_url=compare_url)
