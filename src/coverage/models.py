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
            covered_lines=list(map(int, self.covered_lines.split(","))),
            missing_lines=list(map(int, self.missing_lines.split(","))),
        )


# class TestCoverageModel(Base):
#     __tablename__ = "test_coverage"

#     id = Column(Integer, primary_key=True)

#     # Relationship with CoverageModel
#     cov_list = relationship("CoverageModel", back_populates="test_coverage")

#     # def __init__(self, cov_list: List[CoverageModel], isdiff: bool = False):
#     #     self.isdiff = isdiff
#     #     self.filenames = ",".join([cov.filename for cov in cov_list])

#     #     total_misses = sum(cov.misses for cov in cov_list)
#     #     total_stmts = sum(cov.stmts for cov in cov_list)
#     #     total_covered = sum(cov.covered for cov in cov_list)

#     #     self.total_cov = CoverageModel(
#     #         filename="TOTAL", covered_lines=[], missing_lines=[]
#     #     )
#     #     self.total_cov.misses = total_misses
#     #     self.total_cov.stmts = total_stmts
#     #     self.total_cov.covered = total_covered

#     def deserialize(self) -> TestCoverage:
#         cov_list = [coverage.deserialize() for coverage in self.coverages]
#         return TestCoverage(cov_list=cov_list, isdiff=self.isdiff)
