from cowboy_lib.api.runner.shared import Task

from .service import list_tasks, dequeue_task, complete_task
from .models import CompleteTaskRequest
from .core import TaskQueue, get_queue, get_token_registry, get_token

from fastapi import APIRouter, Depends, HTTPException, Response

from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import CowboyUser

from typing import List

task_queue_router = APIRouter()


@task_queue_router.get("/task/list", response_model=List[Task])
def list(
    task_queue: TaskQueue = Depends(get_queue),
    curr_user: CowboyUser = Depends(get_current_user),
):
    tasks = list_tasks(task_queue=task_queue, user_id=curr_user.id, n=3)
    return tasks


# LAUREN 6: This is where the client gets the task from the queue, and as you can see,
# some jank here


# incredibly hacky, basically, to prevent db connections from being used up
# we exclude db connections for this endpoint, we do the following:
# 1. First request actually does get a db sess, which we use to auth the user
# 2. Grab user id and add it into a in-mem token_registry list
# 3. Return user id as "set-x-task-auth" header
# 4. When the client puts user id into x-task-auth header
# 5. Our DBMiddleware will check the header, and if token is in registry, will not
# add a db session to the request
@task_queue_router.get("/task/get", response_model=List[Task])
def get(
    response: Response,
    task_queue: TaskQueue = Depends(get_queue),
    curr_user: CowboyUser = Depends(get_current_user),
    token_registry: List = Depends(get_token_registry),
    user_token: str = Depends(get_token),
    # perms: str = Depends(PermissionsDependency([TaskGetPermissions])),
):
    # at this point we have passed db user auth; test
    # catches if user sets random token
    if user_token and user_token not in token_registry:
        raise HTTPException(
            status_code=401,
            detail="Token not in registry, cannot proceed. \
            Are you sure you are logged in on the client?",
        )
    # issue token if it does not exist
    elif not user_token:
        print("Setting new token ..")
        response.headers["set-x-task-auth"] = str(curr_user.id)
        token_registry.append(str(curr_user.id))

    tasks = dequeue_task(
        task_queue=task_queue, user_id=curr_user.id if curr_user else int(user_token)
    )
    return tasks


# LAUREN 7: Task is completed by the client
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
