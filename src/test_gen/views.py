from cowboy_lib.repo import SourceRepo
from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import CowboyUser
from src.queue.core import get_queue

from src.test_modules.service import (
    get_all_tms_sorted,
    get_tms_by_filename,
    get_tms_by_names,
)
from src.repo.service import get_or_raise
from src.config import AUTO_GRP_SIZE

from .models import (
    AugmentTestRequest,
    AugmentTestResponse,
    AugmentTestMode,
    UserDecisionRequest,
)
from .augment import augment_test
from .service import save_all, get_test_results, set_test_result_decision
from .service import get_session_id

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
    curr_user: CowboyUser = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    return get_test_results(db_session=db_session, session_id=session_id)


@test_gen_router.post("/test-gen/results/decide")
def set_decision(request: UserDecisionRequest, db_session=Depends(get_db)):
    set_test_result_decision(db_session=db_session, user_decision=request.user_decision)
