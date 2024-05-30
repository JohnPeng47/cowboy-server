from cowboy_lib.repo import SourceRepo, GitRepo
from src.database.core import get_db
from src.auth.service import get_current_user
from src.queue.core import get_queue
from src.stats.service import update_repo_stats

from src.test_modules.service import (
    get_all_tms_sorted,
    get_tms_by_filename,
    get_tms_by_names,
)
from src.repo.service import get_or_raise, get_by_id_or_raise
from src.config import AUTO_GRP_SIZE

from .models import (
    AugmentTestRequest,
    AugmentTestResponse,
    AugmentTestMode,
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
from .service import get_session_id
from .utils import gen_commit_msg

from sqlalchemy.orm import Session
from pathlib import Path
from fastapi import APIRouter, Depends
from functools import reduce
import asyncio

test_gen_router = APIRouter()


@test_gen_router.post("/test-gen/augment", response_model=AugmentTestResponse)
async def augment_test_route(
    request: AugmentTestRequest,
    db_session=Depends(get_db),
    curr_user=Depends(get_current_user),
    task_queue=Depends(get_queue),
    session_id=Depends(get_session_id),
):
    """
    Augment tests for a test module
    """
    repo = get_or_raise(
        db_session=db_session, curr_user=curr_user, repo_name=request.repo_name
    )
    src_repo = SourceRepo(Path(repo.source_folder))

    coroutines = []
    if request.mode == AugmentTestMode.AUTO.value:
        tm_models = get_all_tms_sorted(
            db_session=db_session, src_repo=src_repo, repo_id=repo.id, n=AUTO_GRP_SIZE
        )
    elif request.mode == AugmentTestMode.FILE.value:
        tm_models = get_tms_by_filename(
            db_session=db_session, repo_id=repo.id, src_file=request.src_file
        )
    elif request.mode == AugmentTestMode.TM.value:
        tm_models = get_tms_by_names(
            db_session=db_session, repo_id=repo.id, tm_names=request.tms
        )
    elif request.mode == AugmentTestMode.ALL.value:
        tm_models = get_tms_by_names(
            db_session=db_session, repo_id=repo.id, tm_names=[]
        )

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
