from src.lib.repo.source_file import TestFile, SourceFile, Function, Class

from pathlib import Path
from functools import reduce
from typing import List, Optional, Iterator, Tuple, TYPE_CHECKING
from functools import partial
from logging import getLogger
import os

from src.utils import sync_timed

logger = getLogger("test_results")
longterm_logger = getLogger("longterm")

PATH_EXCLUSIONS = [
    ".venv"
]

# TODO: should we combine git/src_repo into one?
class SourceRepo:
    """
    Used by the TestStrategy to access files and their contents
    """

    def __init__(self, repo_path: Path, files_list: List[str] = []):
        self.repo_path = repo_path
        self.files_list = files_list
        self.source_files: List[SourceFile] = self._init_source_files(files_list, exclusions=PATH_EXCLUSIONS)
        # counter = Counter([f.path for f in self.source_files]).most_common()
        # print(counter)

    def get_rel_path(self, file_path: Path) -> str:
        """
        Get the path relative to the source repo
        """
        return file_path.relative_to(self.repo_path)

    @property
    def test_files(self) -> List[TestFile]:
        return [f for f in self.source_files if isinstance(f, TestFile)]

    @sync_timed
    def _init_source_files(self, files_list=[], exclusions=[]) -> List[TestFile]:
        """
        Finds all test files in the repo
        """
        source_files = []
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                path = Path(root) / file
                if any([ex in str(path) for ex in exclusions]):
                    continue
                if path.is_file() and path.name.endswith(".py"):
                    if files_list:
                        if path not in [self.repo_path / f for f in files_list]:
                            continue
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.read().split("\n")
                    try:
                        rel_path = self.get_rel_path(path)
                        source_file = (
                            TestFile(lines, rel_path)
                            if path.name.startswith("test_")
                            else SourceFile(lines, rel_path)
                        )
                        source_files.append(source_file)
                    except SyntaxError as e:
                        logger.error(f"AST Syntax error while parsing: {path}")

        return source_files

    def find_node(self, name: str, file: str, node_type: str) -> Optional[Function]:
        """
        Finds a function in a file. A node is uniquely identified by its name and filepath
        (local scope)
        """
        for source_file in self.source_files:
            # if str(source_file.path) == file: doesnt work for some reason
            if source_file.path == Path(file):
                for node in source_file.functions + source_file.classes:
                    if node.name == name and node.node_type.value == node_type:
                        return node

        raise Exception(f"Node not found : {name} in {file}")

    def get_test_funcs(self) -> List[Function]:
        return reduce(
            lambda x, y: x + y,
            [test_file.test_funcs() for test_file in self.test_files],
            [],
        )

    def get_test_classes(self) -> List[Class]:
        classes = reduce(
            lambda x, y: x + y,
            [test_file.test_classes() for test_file in self.test_files],
            [],
        )
        return classes

    def iter_tests(self) -> Iterator[Tuple[TestFile, Class]]:
        for test_file in self.test_files:
            for test_class in test_file.test_classes():
                yield test_file, test_class

    def find_file(self, file_path: str) -> Optional[SourceFile]:
        """
        Returns the file object
        """
        for file in self.source_files:
            # NOTE: need path here to deal with consistent / and \ in windows
            if Path(file.path) == Path(file_path):
                return file

    def write_file(self, file_path: str):
        """
        Writes the content of a SourceFile to its original file on disk.
        Note that this API is implemented on SourceRepo because we want
        to control all I/O interactions through this class
        """
        src_file = self.find_file(file_path)
        with open(self.repo_path / file_path, "w") as f:
            f.write(src_file.to_code())
