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
    coverage_id = Column(Integer, ForeignKey("coverage.id", ondelete="CASCADE"))
    coverage = relationship("CoverageModel")

    def __init__(
        self,
        start,
        end,
        lines,
        filepath,
        func_scope,
        class_scope,
        test_module_id,
        coverage_id,
    ):
        self.start = start
        self.end = end
        self.lines = "\n".join(lines)
        self.filepath = str(filepath)
        self.func_scope = func_scope
        self.class_scope = class_scope
        self.test_module_id = test_module_id
        self.coverage_id = coverage_id

    def get_lines(self) -> List[str]:
        return self.lines.split("\n")

    def to_str(self) -> str:
        repr = ""
        repr += f"Chunk: {self.filepath}\n"
        repr += self.lines

        return repr

    def serialize(self, src_repo: SourceRepo):
        return TargetCode(
            range=(self.start, self.end),
            lines=self.get_lines(),
            filepath=Path(self.filepath),
            func_scope=(
                self.func_scope.to_astnode(src_repo) if self.func_scope else None
            ),
            class_scope=(
                self.class_scope.to_astnode(src_repo) if self.class_scope else None
            ),
        )


class TgtCodeDeleteRequest(BaseModel):
    repo_name: str
    tm_name: str
