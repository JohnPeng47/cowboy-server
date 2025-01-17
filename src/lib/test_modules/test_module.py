from typing import List, Optional
from pathlib import Path

from src.lib.coverage import Coverage
from src.lib.repo.source_file import TestFile, ASTNode
from src.lib.utils import get_current_git_commit
from src.lib.repo.source_repo import SourceRepo
from src.lib.test_modules.target_code import TargetCode

class IncompatibleCommit(Exception):
    pass


class TestModule:
    """
    A TestFile with a list of selected Tests
    """
    def __init__(
        self,
        test_file: TestFile,
        is_class: bool,
        name: str,
        commit_sha: str,
        # hack: to check if we are not desync'd from the repo
        check_commit: bool = False,
        chunks: List[TargetCode] = [],
    ):
        test_folder = Path(*test_file.path.parts[:2])
        if check_commit:
            assert commit_sha == get_current_git_commit(test_folder)

        self.commit_sha = commit_sha
        self.test_file = test_file
        # deprecate this
        self.chunks: List[TargetCode] = chunks
        self.target_files: List[Path] = []
        self.cov_diff = None
        self._isclass = is_class
        self.name = name

    def __eq__(self, other: "TestModule"):
        return self.test_file.path + self.name == other.test_file.path + other.name
    
    def to_str(self):
        return str(self.test_file.path) + "::" + self.name 

    @property
    def tests(self) -> List[ASTNode]:
        return (
            [func for func in self.test_file.test_funcs() if not func.scope]
            if not self._isclass
            else [
                func
                for func in self.test_file.test_funcs()
                if func.scope and func.scope.name == self.name
            ]
        )

    @property
    def is_class(self):
        return self._isclass

    def get_targeted_files(self):
        return [Path(f) for f in self.target_files]

    def get_targeted_files_from_chunks(self):
        """
    The list of files that the test module is testing
        """
        # kinda of a hack, but we always assume that base path is in the form
        # repos/<repo_name> appended to the filepath
        # fp = lambda p: base_path if base_path else Path(*p.parts[2:])

        return list(set([c.filepath for c in self.chunks]))

    @property
    def path(self):
        return self.test_file.path

    def target_test_file(self) -> Path:
        """
        Returns the test file that will be modified by test strategy
        to generate new tests
        """
        return self.test_file.path

    def num_lines(self, filename: Optional[str] = ""):
        if not filename:
            chunks = self.chunks
        else:
            chunks = [c for c in self.chunks if c.filepath == filename]

        return sum(
            [c.range[1] - c.range[0] if c.range[1] - c.range[0] else 1 for c in chunks]
        )

    # def get_test_code(self, curr_commit: str):
    #     """
    #     We are purposely including curr_commit here so TestFile will stayed sync'd with fs
    #     Lazily loads the test file just in case we want to setup GitRepo to match
    #     commit_sha. Pass curr_commit as a parameter to double check
    #     """
    #     if curr_commit != self.commit_sha:
    #         raise IncompatibleCommit(
    #             f"curr_commit: {curr_commit} does not match {self.commit_sha}"
    #         )

    #     return "\n\n".join([test.to_code() for test in self.tests])
    
    def get_test_code(self):
        """
        We are purposely including curr_commit here so TestFile will stayed sync'd with fs
        Lazily loads the test file just in case we want to setup GitRepo to match
        commit_sha. Pass curr_commit as a parameter to double check
        """
        return "\n\n".join([test.to_code() for test in self.tests])


    def did_change(self, new_file: TestFile):
        """
        Compares the test file ranges
        """
        for n in new_file.test_nodes:
            for test_node in self.tests:
                if (
                    n.name == test_node.name
                    and n.range != test_node.range
                    # NOTE: this takes into account line additions and deletions
                    # but not modifications, we leaving that for later when the diff
                    # parsing interface gets built
                    and n.range[1] - n.range[0]
                    != test_node.range[1] - test_node.range[0]
                ):
                    new_mods = n.range[1] - n.range[0]
                    old_test = test_node.range[1] - test_node.range[0]
                    if new_mods > old_test:
                        print("Tests were added!")
                    else:
                        print("Tests were deleted!")
                    return True
        return False

    def set_chunks(
        self,
        changed_coverage: List[Coverage],
        source_repo: "SourceRepo",
        base_path: Path = None,
    ):
        """
        Gets the missing/covered lines of each of the coverage differences
        """

        self.chunks = []
        for cov in changed_coverage:
            if cov.filename == "TOTAL":
                raise Exception("TOTAL COVERAGE FILE FOUND")

            cov.read_line_contents(base_path)
            for l_group in cov.get_contiguous_lines():
                start = l_group[0][0]
                end = l_group[-1][0]
                range = (start, end)

                src_file = source_repo.find_file(cov.filename)
                func, cls = src_file.map_line_to_node(start, end)

                lines = [g[1] for g in l_group]

                print("Setting chunk with filepath: ", str(cov.filename))

                chunk = TargetCode(
                    range=range,
                    lines=lines,
                    # could also just move the logic into TestModuleMixin
                    filepath=str(cov.filename),
                    func_scope=func if func else "",
                    class_scope=cls if cls else "",
                )
                self.chunks.append(chunk)

    def delete_chunk(self, range, filepath):
        for c in self.chunks[:]:
            if c.range == range and c.filepath == filepath:
                self.chunks.remove(c)

    def diff_chunks(self, other: "TestModule"):
        return [c for c in self.chunks if c not in other.chunks]

    def print_chunks(self) -> str:
        if not self.chunks:
            return ""

        repr = ""
        repr += f"Test Module: {self.test_file.path}\n"
        repr += f"File: {self.chunks[0].filepath.name}\n"

        curr_file = self.chunks[0].filepath.name
        for c in self.chunks:
            if c.filepath.name != curr_file:
                curr_file = c.filepath.name
                repr += f"File: {c.filepath.name}\n"
            repr += c.to_lines()
        return repr

    def to_json(self):
        return {
            "chunks": [chunk.to_json() for chunk in self.chunks],
            "target_files": [str(f) for f in self.target_files],
            "test_file": self.test_file.to_json(),
            "is_class": self._isclass,           
            "name": self.name,
            "commit_sha": self.commit_sha,
            "cov_diff": self.cov_diff,
        }

    @classmethod
    def from_json(cls, data):
        tm = cls(
            test_file=TestFile.from_json(data["test_file"]),
            is_class=data["is_class"],
            name=data["name"],
            commit_sha=data["commit_sha"],
            chunks=[TargetCode.from_json(chunk) for chunk in data["chunks"]],
        )
        tm.target_files = data["target_files"]
        return tm