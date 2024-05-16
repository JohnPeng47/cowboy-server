from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from pathlib import Path
from typing import List

from cowboy_lib.test_modules.test_module import TestModule
from cowboy_lib.test_modules.target_code import TargetCode
from cowboy_lib.repo.source_repo import SourceRepo

from src.coverage.models import CoverageModel
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
            test_file=src_repo.find_file(Path(self.testfilepath)),
            commit_sha=self.commit_sha,
            nodes=[NodeModel.to_astnode(n, src_repo) for n in self.nodes],
            chunks=[c.serialize(src_repo) for c in self.target_chunks],
        )

    def get_covered_files(self) -> List[str]:
        """
        Returns the source files that are covered by this test module
        """

        # there must be a better way of doing this ...
        return list(set([chunk.filepath for chunk in self.target_chunks]))

    def score(self, filename: str, src_repo: SourceRepo) -> int:
        """
        Get score for a single file
        """
        if filename not in self.get_covered_files():
            raise Exception("Filename is not covered by TM")

        tgt_code_chunks = [
            chunk for chunk in self.target_chunks if chunk.filepath == filename
        ]
        # coverage same for all tgt_code_chunks
        cov = tgt_code_chunks[0].coverage
        file = src_repo.find_file(tgt_code_chunks[0].filepath)
        total_lines = len(file.lines)

        total_covered = cov.covered
        total_missing = cov.misses
        chunk_covered = 0

        for chunk in tgt_code_chunks:
            chunk_covered += len(chunk.get_lines())

        return chunk_covered + total_missing / total_lines if total_lines else 0

    def agg_score(self, src_repo: SourceRepo) -> int:
        """
        Get aggregate score over all covered source files
        """
        agg_score = 0
        all_files = self.get_covered_files()

        for f in all_files:
            agg_score += self.score(f, src_repo)

        return agg_score / len(all_files) if len(all_files) > 0 else 0


class GetTargetCovRequest(BaseModel):
    repo_name: str
    test_modules: List[str]
