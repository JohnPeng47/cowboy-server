from src.database.core import Base
from src.models import CowboyBase

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, validator, model_validator
from enum import Enum
from typing import List
from typing import Optional


class TMSelectMode(str, Enum):
    """
    Used to select the TestModules to be augmented
    """

    AUTO = "auto"
    FILE = "file"
    TM = "module"
    ALL = "all"


class Decision(int, Enum):
    YES = 1
    NO = 0
    UNDECIDED = -1


class TMSelectModeBase(BaseModel):
    mode: TMSelectMode
    files: Optional[List[str]]
    tms: Optional[List[str]]

    @validator("files", always=True)
    def check_files(cls, v, values):
        if values.get("mode") == TMSelectMode.FILE and not v:
            raise ValueError("files must be specified if mode is FILE")
        return v

    @validator("tms", always=True)
    def check_tms(cls, v, values):
        if values.get("mode") == TMSelectMode.TM and not v:
            raise ValueError("tms must be specfied if mode is TM")
        return v


class AugmentTestRequest(TMSelectModeBase):
    repo_name: str


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
    # TODO: not tested yet
    test_module_id = Column(Integer, ForeignKey("test_modules.id"))
    cov_list = relationship("CoverageModel", cascade="all, delete-orphan")

    def set_decision(self, decision: Decision):
        self.decision = decision.value

    def coverage_improve(self):
        return sum([cov.covered for cov in self.cov_list])


class TestResultResponse(BaseModel):
    id: str
    name: str
    test_case: str
    test_file: str
    cov_improved: int
    decided: int


class UserDecision(BaseModel):
    id: int
    decision: Decision


class UserDecisionRequest(BaseModel):
    user_decision: List[UserDecision]

    @model_validator(mode="before")
    def check_user_decision(cls, values):
        if not values.get("user_decision"):
            raise ValueError("user_decision must not be empty")
        return values


class UserDecisionResponse(BaseModel):
    compare_url: str
