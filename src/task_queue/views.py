from .service import list_tasks
from .models import ListTasks
from fastapi import APIRouter, Depends

from src.task_queue.core import TaskQueue, get_queue
from src.auth.service import get_current_user
from src.auth.models import CowboyUser


task_queue_router = APIRouter()


@task_queue_router.get("/task/list", response_model=ListTasks)
def list(
    task_queue: TaskQueue = Depends(get_queue),
    curr_user: CowboyUser = Depends(get_current_user),
):
    tasks = list_tasks(task_queue=task_queue, user_id=curr_user.id, n=3)
    return ListTasks(tasks=tasks)
