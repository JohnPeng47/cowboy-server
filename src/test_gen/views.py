from cowboy_lib.repo import SourceRepo
from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import CowboyUser
from src.queue.core import get_queue

from src.test_modules.service import get_all_tms_sorted, get_tms_by_filename
from src.repo.service import get as get_repo
from src.models import HTTPSuccess

from .models import AugmentTestRequest, AugmentTestMode, UserDecisionRequest
from .augment import augment_test
from .service import save_all, get_test_results, set_test_result_decision

from sqlalchemy.orm import Session
from pathlib import Path
from fastapi import APIRouter, Depends
import asyncio
from functools import reduce

test_gen_router = APIRouter()


@test_gen_router.post("/test-gen/augment")
async def augment_test_route(
    request: AugmentTestRequest,
    db_session=Depends(get_db),
    curr_user=Depends(get_current_user),
    task_queue=Depends(get_queue),
):
    """
    Augment tests for a test module
    """
    repo = get_repo(
        db_session=db_session, curr_user=curr_user, repo_name=request.repo_name
    )
    src_repo = SourceRepo(Path(repo.source_folder))

    coroutines = []
    if request.mode == AugmentTestMode.AUTO.value:
        tm_models = get_all_tms_sorted(
            db_session=db_session, src_repo=src_repo, repo_id=repo.id, n=2
        )
    elif request.mode == AugmentTestMode.FILE.value:
        tm_models = get_tms_by_filename(
            db_session=db_session, repo_id=repo.id, src_file=request.src_file
        )

    for tm_model in tm_models:
        coroutine = augment_test(
            db_session=db_session,
            task_queue=task_queue,
            repo=repo,
            tm_model=tm_model,
            curr_user=curr_user,
            repo_name=request.repo_name,
        )
        coroutines.append(coroutine)

    test_results = await asyncio.gather(*coroutines)
    test_results = reduce(lambda x, y: x + y, test_results)

    # we save here after async ops have finished running
    save_all(db_session=db_session, test_results=test_results)

    return HTTPSuccess()


@test_gen_router.get("/test-gen/results/{repo_name}")
def get_results(
    repo_name: str,
    curr_user: CowboyUser = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    repo = get_repo(db_session=db_session, curr_user=curr_user, repo_name=repo_name)
    return get_test_results(db_session=db_session, repo_id=repo.id)


@test_gen_router.post("/test-gen/results/decide")
def set_decision(request: UserDecisionRequest, db_session=Depends(get_db)):
    set_test_result_decision(db_session=db_session, user_decision=request.user_decision)


@test_gen_router.post("/test-gen/results/{repo_name}/clean")
def clean_results(repo_name: str, db_session=Depends(get_db)):
    """
    Removes all test results that have not been
    """
    repo = get_repo(db_session=db_session, repo_name=repo_name)
