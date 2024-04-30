from fastapi import Request
from queue import Queue

from threading import Lock
from collections import defaultdict

from typing import List
from asyncio import Event

from .models import Task, TaskStatus
from src.utils import generate_id
from typing import Dict


class TaskEvent:
    def __init__(self, task: Task):
        self.event = Event()
        self.task = task
        self.result = None

    async def wait(self):
        await self.event.wait()
        return self.result

    def complete(self, result):
        """
        Complete with result and signal event to wake up
        """
        self.result = result
        self.event.set()

    @property
    def task_id(self):
        return self.task.task_id

    def __eq__(self, other):
        return self.task_id == other.task_id

    # def __hash__(self):
    #     return sum([ord(c) for c in self.task_id])


class TaskQueue:
    """
    A set of queues separated by user_id
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            print("Creating new TaskQueue instance")
            cls._instance = super(TaskQueue, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False

        return cls._instance

    def __init__(self):
        if not self._initialized:
            # Initialize instance variables only once
            self.queue: Dict[str, List[TaskEvent]] = defaultdict(list)
            self.locks = defaultdict(list)
            self._initialized = True  # Mark as initialized

    def _acquire_lock(self, user_id: int):
        if self.locks.get(user_id, None) is None:
            self.locks[user_id] = Lock()
        return self.locks.get(user_id)

    def put(self, user_id: int, task: str) -> TaskEvent:
        with self._acquire_lock(user_id):
            t = TaskEvent(task)
            self.queue[user_id].append(t)

            return t

    def complete(self, user_id: int, task_id: str, res):
        with self._acquire_lock(user_id):
            for i in range(len(self.queue[user_id])):
                if self.queue[user_id][i].task_id == task_id:
                    t = self.queue[user_id].pop(i)
                    t.complete(res)
                    break

    # def get(self, user_id: int) -> Task:
    #     """
    #     Returns the first PENDING task and changes its status to STARTED
    #     """
    #     with self._acquire_lock(user_id):
    #         if len(self.queue[user_id]) == 0:
    #             return None

    #         return self.queue[user_id].pop()

    def get_all(self, user_id: int) -> List[Task]:
        with self._acquire_lock(user_id):
            if len(self.queue[user_id]) == 0:
                return []

            tasks = []
            for t in filter(
                lambda t: t.task.status == TaskStatus.PENDING.value, self.queue[user_id]
            ):
                t.task.status = TaskStatus.STARTED.value
                tasks.append(t.task)

            return tasks

    def peak(self, user_id: int, n: int) -> List[Task]:
        """
        Get the first n tasks in queue without removing
        """
        with self._acquire_lock(user_id):
            if len(self.queue[user_id]) == 0:
                return []

            return [t.task for t in self.queue[user_id][:n]]


def get_queue(request: Request):
    return request.state.task_queue
