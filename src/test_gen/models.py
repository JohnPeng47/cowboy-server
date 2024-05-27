from src.database.core import Base
from src.models import CowboyBase

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, validator
from enum import Enum
from typing import List
from typing import Optional


class AugmentTestMode(str, Enum):
    AUTO = "auto"
    FILE = "file"
    TM = "module"
    ALL = "all"


class Decision(int, Enum):
    YES = 1
    NO = 0
    UNDECIDED = -1


class AugmentTestRequest(BaseModel):
    repo_name: str
    mode: AugmentTestMode
    src_file: Optional[str]
    tms: Optional[List[str]]

    @validator("src_file", always=True)
    def check_src_file(cls, v, values):
        if values.get("mode") == AugmentTestMode.FILE and not v:
            raise ValueError("src_file must be specified if mode is FILE")
        return v

    @validator("tms", always=True)
    def check_tms(cls, v, values):
        if values.get("mode") == AugmentTestMode.TM and not v:
            raise ValueError("tms must be specfied if mode is TM")
        return v


class AugmentTestResponse(CowboyBase):
    session_id: str


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
    session_id = Column(String)

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
