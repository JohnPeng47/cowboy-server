from src.database.core import Base, Session

from typing import Optional

from .models import Queue, Task, TaskStatus


def dequeue_task(*, db_session: Session, queue_id: int) -> Optional[Task]:
    """Dequeue the first task in the queue: retrieve and delete it."""
    queue = db_session.query(Queue).filter(Queue.id == queue_id).one_or_none()
    if queue and queue.tasks:
        task = queue.tasks[0]
        db_session.delete(task)
        db_session.commit()
        return task
    return None


def enqueue_task(*, db_session: Session, queue_id: int, task: Task) -> None:
    """Enqueue a task to the specified queue."""
    task.queue_id = queue_id
    db_session.add(task)
    db_session.commit()
