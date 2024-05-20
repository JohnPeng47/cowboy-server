from fastapi import APIRouter, Depends, BackgroundTasks

from src.database.core import get_db
from src.auth.service import get_current_user, CowboyUser
from src.queue.core import TaskQueue, get_queue
from src.models import HTTPSuccess
from src.repo.service import get as get_repoconf
from src.tasks.create_tgt_coverage import create_tgt_coverage

from .models import GetTargetCovRequest

from sqlalchemy.orm import Session
import asyncio


tm_router = APIRouter()


@tm_router.post("/tm/baseline", response_model=HTTPSuccess)
async def get_tm_target_coverage(
    request: GetTargetCovRequest,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    repo_conf = get_repoconf(
        db_session=db_session, curr_user=current_user, repo_name=request.repo_name
    )

    # When ran like this, task execution does not continue execuing the await block
    # inside get_tgt_coverage after a task has been updated by the client
    # background_tasks.add_task(
    #     get_tgt_coverage,
    #     task_queue=task_queue,
    #     curr_user=current_user,
    #     repo_config=repo_conf,
    #     tm_names=request.test_modules,
    # )

    # NOTE: don't need to await here because we dont need to return the result right away
    asyncio.create_task(
        create_tgt_coverage(
            db_session=db_session,
            task_queue=task_queue,
            curr_user=current_user,
            repo_config=repo_conf,
            tm_names=request.test_modules,
        )
    )

    # background_tasks.add_task(await_future)

    return HTTPSuccess()
