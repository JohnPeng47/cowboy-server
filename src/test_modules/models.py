from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from pydantic import BaseModel

from pathlib import Path

from typing import List
from logging import getLogger

from cowboy_lib.repo.source_repo import SourceRepo
from src.database.core import Base
from src.ast.models import NodeModel

from cowboy_lib.test_modules.test_module import TestModule
from cowboy_lib.test_modules.target_code import TargetCode


class IncompatibleCommit(Exception):
    pass


class TestModuleModel(Base):
    __tablename__ = "test_modules"
    id = Column(Integer, primary_key=True)
    testfilepath = Column(String)
    commit_sha = Column(String)

    repo_id = Column(Integer, ForeignKey("repo_config.id"))
    nodes = relationship("NodeModel", backref="test_modules")

    def serialize(self, source_repo: SourceRepo) -> TestModule:
        return TestModule(
            test_file=source_repo.get_file(Path(self.testfilepath)),
            commit_sha=self.commit_sha,
            nodes=[NodeModel.to_astnode(n) for n in self.nodes],
        )

    @classmethod
    def deserialize(cls, tm: TestModule) -> "TestModuleModel":
        return cls(
            test_file=tm.test_file.path,
            commit_sha=tm.commit_sha,
            nodes=[NodeModel.to_astnode(n) for n in tm.nodes],
        )


class TargetCodeModel(Base):
    """
    A chunk of code that is covered by the lines in a TestModule
    """

    __tablename__ = "target_code"
    id = Column(Integer, primary_key=True)
    range = Column(String)
    lines = Column(String)
    filepath = Column(String)
    func_scope = Column(String)
    class_scope = Column(String)

    # node_id = Column(Integer, ForeignKey("nodes.id"))

    def serialize(self):
        return TargetCode(
            range=self.range,
            lines=self.lines,
            filepath=str(self.filepath),
            func_scope=self.func_scope,
            class_scope=self.class_scope,
        )

    @classmethod
    def deserialize(cls, model: TargetCode):
        return cls(
            range=model.range,
            lines=model.lines,
            filepath=Path(model.filepath),
            func_scope=model.func_scope,
            class_scope=model.class_scope,
        )


class GetTargetCovRequest(BaseModel):
    repo_name: str
    test_modules: List[str]
