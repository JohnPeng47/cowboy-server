from fastapi import APIRouter, Depends

from cowboy_lib.repo import SourceRepo

from src.database.core import get_db
from src.queue.core import TaskQueue, get_queue
from src.auth.service import get_current_user, CowboyUser
from src.repo.service import get_or_raise
from src.test_gen.service import select_tms

from src.models import HTTPSuccess
from src.tasks.create_tgt_coverage import create_tgt_coverage
from src.runner.models import ClientRunnerException

from .models import BuildMappingRequest

from sqlalchemy.orm import Session
from pathlib import Path

tm_router = APIRouter()


@tm_router.post("/tm/build-mapping")
async def get_tm_target_coverage(
    request: BuildMappingRequest,
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    repo = get_or_raise(
        db_session=db_session, curr_user=current_user, repo_name=request.repo_name
    )
    src_repo = SourceRepo(Path(repo.source_folder))
    tm_models = select_tms(
        db_session=db_session, repo_id=repo.id, request=request, src_repo=src_repo
    )

    try:
        await create_tgt_coverage(
            db_session=db_session,
            task_queue=task_queue,
            curr_user=current_user,
            repo_config=repo,
            tm_models=tm_models,
            overwrite=request.overwrite,
        )

        return HTTPSuccess()

    except ClientRunnerException as e:
        raise e
