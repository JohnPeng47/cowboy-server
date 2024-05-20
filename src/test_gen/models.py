from src.database.core import Base
from src.models import CowboyBase

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from enum import Enum
from typing import List
from typing import Optional


class AugmentTestMode(str, Enum):
    AUTO = "auto"
    FILE = "file"


class Decision(int, Enum):
    YES = 1
    NO = 0
    UNDECIDED = -1


class AugmentTestRequest(BaseModel):
    repo_name: str
    src_file: Optional[str]
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
    decide = Column(Integer, default=-1)
    commit_hash = Column(String)

    # used in TestFile.append() to construct the modified test file
    testfile = Column(String)
    classname = Column(String, nullable=True)

    repo_id = Column(Integer, ForeignKey("repo_config.id"))
    test_module_id = Column(Integer, ForeignKey("test_modules.id"))
    cov_list = relationship("CoverageModel")

    def set_decision(self, decision: Decision):
        self.decision = decision.value


class UserDecision(BaseModel):
    id: int
    decision: Decision


class UserDecisionRequest(BaseModel):
    user_decision: List[UserDecision]
