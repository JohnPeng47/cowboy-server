from cowboy_lib.api.runner.shared import Task

from .service import list_tasks, dequeue_task, complete_task
from .models import CompleteTaskRequest
from .permissions import TaskGetPermissions
from .core import TaskQueue, get_queue, get_token_registry, get_token

from fastapi import APIRouter, Depends, HTTPException, Response

from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import CowboyUser
from src.auth.permissions import PermissionsDependency

from typing import List

task_queue_router = APIRouter()


@task_queue_router.get("/task/list", response_model=List[Task])
def list(
    task_queue: TaskQueue = Depends(get_queue),
    curr_user: CowboyUser = Depends(get_current_user),
):
    tasks = list_tasks(task_queue=task_queue, user_id=curr_user.id, n=3)
    return tasks


@task_queue_router.get("/task/get", response_model=List[Task])
def get(
    response: Response,
    task_queue: TaskQueue = Depends(get_queue),
    curr_user: CowboyUser = Depends(get_current_user),
    token_registry: List = Depends(get_token_registry),
    token: str = Depends(get_token),
    db=Depends(get_db),
    perms: str = Depends(PermissionsDependency([TaskGetPermissions])),
):
    print("Token", token, "DB: ", db.is_active, db.id)

    # at this point we have passed db user auth; test
    # catches if user sets random token
    if token and token not in token_registry:
        raise HTTPException(
            status_code=401, detail="Token not in registry, cannot proceed"
        )
    # issue token if it does not exist
    elif not token:
        print("setting token")
        token = "1234hello"
        response.headers["set-x-task-auth"] = token
        token_registry.append(token)

    tasks = dequeue_task(task_queue=task_queue, user_id=curr_user.id)
    return tasks


@task_queue_router.post("/task/complete", response_model=CompleteTaskRequest)
def complete(
    task: CompleteTaskRequest,
    task_queue: TaskQueue = Depends(get_queue),
    curr_user: CowboyUser = Depends(get_current_user),
):

    task_queue = complete_task(
        task_queue=task_queue,
        user_id=curr_user.id,
        task_id=task.task_id,
        result=task.result,
    )
    return task
