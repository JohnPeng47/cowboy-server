from .service import list_tasks, dequeue_task, complete_task
from .models import Task, GetTaskResponse, CompleteTaskRequest
from fastapi import APIRouter, Depends

from src.task_queue.core import TaskQueue, get_queue
from src.auth.service import get_current_user
from src.auth.models import CowboyUser

from typing import List, Optional

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
    task_queue: TaskQueue = Depends(get_queue),
    curr_user: CowboyUser = Depends(get_current_user),
):
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
