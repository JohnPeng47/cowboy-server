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
from src.target_code.models import TargetCodeModel


class IncompatibleCommit(Exception):
    pass


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
