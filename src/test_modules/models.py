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

    def __init__(
        self,
        start,
        end,
        lines,
        filepath,
        func_scope,
        class_scope,
        test_module_id,
    ):
        self.start = start
        self.end = end
        self.lines = "\n".join(lines)
        self.filepath = str(filepath)
        self.func_scope = func_scope
        self.class_scope = class_scope
        self.test_module_id = test_module_id

    def serialize(self, src_repo: SourceRepo):
        return TargetCode(
            range=(self.start, self.end),
            lines=self.lines.split("\n"),
            filepath=Path(self.filepath),
            func_scope=(
                self.func_scope.to_astnode(src_repo) if self.func_scope else None
            ),
            class_scope=(
                self.class_scope.to_astnode(src_repo) if self.class_scope else None
            ),
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

    def serialize(self, src_repo: SourceRepo) -> TestModule:
        """
        Convert model back to TestModule
        """

        return TestModule(
            test_file=src_repo.get_file(Path(self.testfilepath)),
            commit_sha=self.commit_sha,
            nodes=[NodeModel.to_astnode(n, src_repo) for n in self.nodes],
            chunks=[c.serialize(src_repo) for c in self.target_chunks],
        )


class GetTargetCovRequest(BaseModel):
    repo_name: str
    test_modules: List[str]
