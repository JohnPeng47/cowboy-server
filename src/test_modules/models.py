from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from pathlib import Path
from typing import List

from cowboy_lib.test_modules.test_module import TestModule
from cowboy_lib.test_modules.target_code import TargetCode
from cowboy_lib.repo.source_repo import SourceRepo
from src.database.core import Base
from src.ast.models import NodeModel


class IncompatibleCommit(Exception):
    pass


class TargetCodeModel(Base):
    """
    A chunk of code that is covered by the lines in a TestModule
    """

    __tablename__ = "target_code"
    id = Column(Integer, primary_key=True)
    start = Column(Integer)
    end = Column(Integer)
    lines = Column(String)
    filepath = Column(String)

    func_scope = relationship(
        "NodeModel",
        foreign_keys=[NodeModel.target_code_id],
        cascade="all, delete",
        uselist=False,
        single_parent=True,
    )
    class_scope = relationship(
        "NodeModel",
        foreign_keys=[NodeModel.target_code_id],
        cascade="all, delete",
        uselist=False,
        single_parent=True,
    )

    test_module_id = Column(Integer, ForeignKey("test_modules.id", ondelete="CASCADE"))

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


class TestModuleModel(Base):
    __tablename__ = "test_modules"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    testfilepath = Column(String)
    commit_sha = Column(String)

    repo_id = Column(Integer, ForeignKey("repo_config.id"))
    nodes = relationship(
        "NodeModel",
        backref="test_module",
        foreign_keys=[NodeModel.test_module_id],
        cascade="all, delete-orphan",
    )
    target_chunks = relationship(
        "TargetCodeModel",
        backref="test_module",
        foreign_keys=[TargetCodeModel.test_module_id],
        cascade="all, delete-orphan",
    )

    def serialize(self, source_repo: SourceRepo) -> TestModule:
        """
        Convert model back to TestModule
        """

        return TestModule(
            test_file=source_repo.get_file(Path(self.testfilepath)),
            commit_sha=self.commit_sha,
            nodes=[NodeModel.to_astnode(n, source_repo) for n in self.nodes],
        )


class GetTargetCovRequest(BaseModel):
    repo_name: str
    test_modules: List[str]
