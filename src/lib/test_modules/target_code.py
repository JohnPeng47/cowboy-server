from dataclasses import dataclass

from typing import List, Optional, TYPE_CHECKING, Tuple
from pathlib import Path

from src.lib.ast.code import ASTNode


@dataclass
class TargetCode:
    """
    A chunk of code that is covered by the lines in a TestModule
    """

    range: Tuple[int, int]
    lines: List[str]
    filepath: Path
    func_scope: Optional[ASTNode]
    class_scope: Optional[ASTNode]

    def base_path(self) -> Path:
        """
        Returns the base path relative to the repo directory
        """
        return Path(*self.filepath.parts[2:])

    def __post_init__(self):
        if not isinstance(self.filepath, Path):
            self.filepath = Path(self.filepath)

    def __eq__(self, other: "TargetCode"):
        return self.filepath == other.filepath and self.range == other.range

    def __hash__(self):
        return hash((self.filepath, self.range))

    def to_lines(self):
        repr = ""
        for i, line in zip(range(self.range[0], self.range[1] + 1), self.lines):
            repr += f"{i}. {line}\n"

        return repr

    def to_str(self) -> str:
        repr = ""
        repr += f"Chunk: {self.filepath}\n"
        repr += self.lines

        return repr
    
    def to_json(self):
        return {
            "range": self.range,
            "lines": self.lines,
            "filepath": str(self.filepath),
            "func_scope": self.func_scope.to_json() if self.func_scope else None,
            "class_scope": self.class_scope.to_json() if self.class_scope else None,
        }

    @classmethod
    def from_json(cls, data):
        return cls(
            range=data["range"],
            lines=data["lines"],
            filepath=Path(data["filepath"]),
            func_scope=ASTNode.from_json(data["func_scope"]) if data.get("func_scope") else None,
            class_scope=ASTNode.from_json(data["class_scope"]) if data.get("class_scope") else None,
        )
