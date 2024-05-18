from pydantic import BaseModel
from enum import Enum
from typing import List

from src.database.core import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from src.models import CowboyBase

from typing import Optional


class AugmentTestMode(str, Enum):
    AUTO = "auto"
    FILE = "file"


class Feedback(int, Enum):
    YES = 1
    NO = 0
    UNDECIDED = -1


class AugmentTestRequest(BaseModel):
    src_file: Optional[str]
    repo_name: str
    mode: AugmentTestMode


class AugmentTestResponse(CowboyBase):
    id: int
    name: str
    test_case: str


class AugmentTestResult(Base):
    __tablename__ = "augment_test_results"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    test_case = Column(String)
    cov_plus = Column(Integer)  # additional coverage gained
    feedback = Column(Integer, default=-1)
    commit_hash = Column(String)

    # used in TestFile.append() to construct the modified test file
    testfile = Column(String)
    classname = Column(String, nullable=True)

    test_module_id = Column(Integer, ForeignKey("test_modules.id"))

    def set_feedback(self, feedback: Feedback):
        self.feedback = feedback.value
