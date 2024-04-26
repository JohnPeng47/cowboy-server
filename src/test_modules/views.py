from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from src.database.core import Session, get_db
from src.auth.service import get_current_user, CowboyUser

from src.task_queue.core import TaskQueue, get_queue
from src.models import HTTPSuccess
from src.repo.service import get as get_repoconf

from .models import GetTargetCovRequest
from .service import get_tgt_coverage


tm_router = APIRouter()


@tm_router.post("/tm/baseline", response_model=HTTPSuccess)
def get_tm_target_coverage(
    request: GetTargetCovRequest,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    repo_conf = get_repoconf(
        db_session=db_session, curr_user=current_user, repo_name=request.repo_name
    )

    background_tasks.add_task(
        get_tgt_coverage,
        task_queue=task_queue,
        curr_user=current_user,
        repo_config=repo_conf,
        tm_names=request.test_modules,
    )

    return HTTPSuccess()
