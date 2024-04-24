from sqlalchemy import create_engine, Column, String, JSON, Integer
from sqlalchemy.orm import relationship

from uuid import uuid4
from enum import Enum

from src.database.core import Base


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class Task(Base):
    """
    Database task, tied to a parent job.
    """

    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    result = Column(JSON, default=dict)
    status = Column(String, default=TaskStatus.PENDING.value)
    name = Column(String, default="")


class Queue(Base):
    __tablename__ = "queues"

    id = Column(Integer, primary_key=True)
    name = Column(String, default="")
    tasks = relationship("Task", backref="queue", order_by="Task.id")
