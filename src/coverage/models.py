from cowboy_lib.coverage import Coverage, TestCoverage

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.database.core import Base
from typing import List


class CoverageModel(Base):
    __tablename__ = "coverage"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    covered_lines = Column(String, nullable=False)
    missing_lines = Column(String, nullable=False)

    stmts = Column(Integer, nullable=False)
    misses = Column(Integer, nullable=False)
    covered = Column(Integer, nullable=False)

    # test_coverage_id = Column(Integer, ForeignKey("test_coverage.id"))
    target_code_list = relationship(
        "TargetCodeModel", back_populates="coverage", cascade="all, delete-orphan"
    )
    repo_id = Column(Integer, ForeignKey("repo_config.id"))
    test_result_id = Column(Integer, ForeignKey("augment_test_results.id"))

    def deserialize(self) -> Coverage:
        return Coverage(
            filename=self.filename,
            covered_lines=[int(l) for l in self.covered_lines.split(",") if l],
            missing_lines=[int(l) for l in self.missing_lines.split(",") if l],
        )
