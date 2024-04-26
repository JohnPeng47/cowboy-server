from fastapi import Request
from queue import Queue

from threading import Lock
from collections import defaultdict


class TaskQueue:
    """
    A set of queues separated by user_id
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            print("Creating new TaskQueue instance")
            cls._instance = super(TaskQueue, cls).__new__(cls, *args, **kwargs)
            cls._instance.queue = defaultdict(list)
            cls._instance.locks = defaultdict(list)
        return cls._instance

    def acquire_lock(self, user_id: int):
        if self.locks.get(user_id, None) is None:
            self.locks[user_id] = Lock()
        return self.locks.get(user_id)

    def put(self, user_id: int, task: str):
        with self.acquire_lock(user_id):
            self.queue[user_id].append(task)

    def get(self, user_id: int):
        with self.acquire_lock(user_id):
            if len(self.queue[user_id]) == 0:
                return None

            return self.queue[user_id].pop()

    def get_all(self, user_id: int):
        with self.acquire_lock(user_id):
            tasks = []
            while len(self.queue[user_id]) > 0:
                tasks.append(self.queue[user_id].pop(0))

            return tasks

    def peak(self, user_id: int, n: int):
        """
        Get the first n tasks in queue without removing
        """
        with self.acquire_lock(user_id):
            if len(self.queue[user_id]) == 0:
                return []

            return self.queue[user_id][:n]


def get_queue(request: Request):
    return request.state.task_queue
