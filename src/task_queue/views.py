from .service import list_tasks, dequeue_task
from .models import ListTasksResponse, GetTaskResponse
from fastapi import APIRouter, Depends

from src.task_queue.core import TaskQueue, get_queue
from src.auth.service import get_current_user
from src.auth.models import CowboyUser


task_queue_router = APIRouter()


@task_queue_router.get("/task/list", response_model=ListTasksResponse)
def list(
    task_queue: TaskQueue = Depends(get_queue),
    curr_user: CowboyUser = Depends(get_current_user),
):
    tasks = list_tasks(task_queue=task_queue, user_id=curr_user.id, n=3)
    print(tasks)
    return ListTasksResponse(tasks=tasks)


@task_queue_router.get("/task/get", response_model=ListTasksResponse)
def get(
    task_queue: TaskQueue = Depends(get_queue),
    curr_user: CowboyUser = Depends(get_current_user),
):
    tasks = dequeue_task(task_queue=task_queue, user_id=curr_user.id)
    return ListTasksResponse(tasks=tasks)
