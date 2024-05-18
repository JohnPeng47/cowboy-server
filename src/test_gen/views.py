from cowboy_lib.repo import SourceRepo
from src.database.core import get_db
from src.auth.service import get_current_user
from src.queue.core import get_queue

from src.test_modules.service import get_all_tms_sorted, get_tms_by_filename
from src.repo.service import get as get_repo

from .models import AugmentTestRequest, AugmentTestMode, AugmentTestResponse
from .augment import augment_test

from pathlib import Path
from fastapi import APIRouter, Depends
import asyncio
from functools import reduce
from typing import List, Optional

test_gen_router = APIRouter()


@test_gen_router.post("/test-gen/augment")
async def augment_test_route(
    request: AugmentTestRequest,
    db_session=Depends(get_db),
    curr_user=Depends(get_current_user),
    task_queue=Depends(get_queue),
):
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
        print(tm_models)

    for tm_model in tm_models:
        print("Augmenting model: ", tm_model.name)
        coroutine = augment_test(
            task_queue=task_queue,
            repo=repo,
            tm_model=tm_model,
            curr_user=curr_user,
            repo_name=request.repo_name,
        )
        coroutines.append(coroutine)

    test_results = await asyncio.gather(*coroutines)
    test_results = reduce(lambda x, y: x + y, test_results)

    print(test_results)
    return test_results
