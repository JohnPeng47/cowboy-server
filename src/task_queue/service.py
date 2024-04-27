from src.database.core import Base, Session
from queue import Queue

from typing import Optional, List
from .models import Task, TaskStatus

from src.task_queue.core import TaskQueue
from src.auth.models import CowboyUser


def list_tasks(*, task_queue: TaskQueue, user_id: int, n: int) -> Optional[List[Task]]:
    """List all tasks in the queue."""

    return task_queue.peak(user_id, n)


def dequeue_task(
    *, task_queue: TaskQueue, task: Task, user_id: int
) -> Optional[List[Task]]:
    """Dequeue the first task in the queue: retrieve and delete it."""

    return task_queue.get_all(user_id)


async def enqueue_task_and_wait(
    *, task_queue: TaskQueue, task: Task, user_id: int
) -> None:
    """Enqueue a task to the specified queue."""

    f = task_queue.put(user_id, task)
    return await f.wait()
