from typing import NamedTuple, Optional, List, Dict, Iterable, Tuple
from pathlib import Path
from itertools import product
from typing import List, Tuple, NewType, Dict, Union
import re


from logging import getLogger

logger = getLogger("test_results")


class CoverageException(Exception):
    pass


class CoverageFailure(Exception):
    pass


class CoverageSubtractionError(Exception):
    def __init__(self, cov1, cov2, filename):
        super().__init__(f"Negative value in coverage {cov1 - cov2} for {filename}")


def get_full_path(base_path: Path, filename: str):
    """
    Join filename, which is relative to the source repo root to the base repo path, while
    also converting it to use the same Path format (WindowsPath or PosixPath)
    """
    filename = filename.replace("\\", "/")
    return Path(base_path / filename)

class Coverage:
    def __init__(
        self,
        filename: str,
        covered_lines: List[int],
        missing_lines: List[int],
    ):
        self.all_lines = covered_lines + missing_lines
        # self.all_lines = list(set(self.all_lines))
        # assert len(self.all_lines) == len(set(self.all_lines))

        # self.cov: int = cov
        self.covered_lines: List[int] = covered_lines
        self.missing_lines: List[int] = missing_lines

        self.stmts: int = len(self.all_lines)
        self.misses: int = len(self.missing_lines)
        self.covered: int = len(self.covered_lines)

        # if covered_lines and missing_lines:
        #     for line in covered_lines:
        #         if line in missing_lines:
        #             raise CoverageException(
        #                 f"Line {line} is both covered and missing in {filename}"
        #             )

        self.filename = self.convert_path(filename)

        # defer initialization
        self._covered_lines_dict: Dict[int, str] = {}
        self._miss_lines_dict: Dict[int, str] = {}

    def convert_path(self, filename: str):
        """
        Converts the path to a Unix-style path
        """
        return filename.replace("\\", "/")

    @property
    def cov(self) -> float:
        return self.covered / self.stmts

    def __eq__(self, other: Optional["Coverage"]):
        # None comparison
        if not other:
            if (
                self.filename == None
                and self.stmts == None
                and self.misses == None
                and self.covered == None
                and self.cov == None
            ):
                return True
            return False

        elif isinstance(other, Coverage):
            if (
                self.filename == other.filename
                and self.stmts == other.stmts
                and self.misses == other.misses
                and self.covered == other.covered
                and self.cov == other.cov
            ):
                return True
            return False

        else:
            raise CoverageException("Comparisons only allowed for Coverage or None")

    def __sub__(self, other: "Coverage"):
        if not isinstance(other, Coverage):
            raise CoverageException(f"Assertion failed: other must be a Coverage instance: {self.filename}")
        if self.filename != other.filename:
            raise CoverageException(f"Assertion failed: filenames must match: {self.filename}")
        
        # Removing this check because coveragepy has a bug where deselected lines containing a multi-line string """
        # are not counted towards deselected lines causing stmts counts to be mismatched
        # if self.stmts != other.stmts:
        #     raise CoverageException(f"Assertion failed: statement counts must match: {self.filename}")

        # NOTE:
        # use set sub here to find only the overlapping missing lines
        # for eg.
        # a_miss = [1,2,3]
        # b_miss = [1,2,4]
        # if we just sub the abs len of missing lines, we would get:
        # a_miss - b_miss = []
        # but instead we want:
        # a_miss - b_miss = [3]
        # Because we want to if b improved the coverage of a
        added_lines = set(self.covered_lines) - set(other.covered_lines)
        missing_lines = set(self.all_lines) - added_lines

        cov = Coverage(
            self.filename,
            covered_lines=list(added_lines),
            missing_lines=list(missing_lines),
        )
        # seomthing is wrong here!
        # need to do this to support negative coverage
        cov.covered = self.covered - other.covered
        # if cov.covered < 0 and cov.covered_lines:
        #     # theoretically shud not happen, except in case
        #     # where a covered test causes another test to fail
        #     raise CoverageSubtractionError(self.covered, other.covered, self.filename)
        #     print("Negative coverage in ", self.filename, cov.covered)

        return cov

    def __add__(self, other: "Coverage"):
        """
        Unlike sub, we can only add the covered from other if it does not overlap
        with a pre-exsiting line
        """
        if not isinstance(other, Coverage):
            raise CoverageException(f"Assertion failed: other must be a Coverage instance: {self.filename}")
        if self.filename != other.filename:
            raise CoverageException(f"Assertion failed: filenames must match: {self.filename}")
        # Removing check for now cuz for some reason coveragepy does not take into account deleselected lines
        # in its aggregate stmts, making the stmt count inconsistent when comparing against a file with deselected tests
        # if self.stmts != other.stmts:
        #     raise CoverageException(f"Assertion failed: statement counts must match: {self.filename}")

        added_lines = set(other.covered_lines) - set(self.covered_lines)
        missing_lines = set(self.all_lines) - set(self.covered_lines) - added_lines

        return Coverage(
            self.filename,
            covered_lines=list(set(self.covered_lines).union(added_lines)),
            missing_lines=list(missing_lines),
        )

    @classmethod
    def diff_cov(cls, a: "Coverage", b: "Coverage", keep_line: int) -> "Coverage":
        """
        Gets the diff between two coverages that also includes covered_lines
        """
        assert keep_line in [1, 2]

        cov_diff = a - b

        sub1 = set(a.covered_lines) if keep_line == 1 else set(b.covered_lines)
        sub2 = set(b.covered_lines) if keep_line == 1 else set(a.covered_lines)
        if len(sub1) < len(sub2):
            logger.warn("a < b in the subtraction of covered lines, is this expected?")

        covered_lines = sub1 - sub2
        cov_diff.covered_lines = list(covered_lines)
        return cov_diff

    def __str__(self):

        return f"Coverage: {self.filename}, stmts: {self.stmts}, misses: {self.misses}, covered: {self.covered}"

    def read_line_contents(self, base_path: Path):
        """
        Lazily reads the line contents of the file
        """
        fp = get_full_path(base_path, self.filename)

        with open(fp, "r", encoding="utf-8") as file:
            # print("Covered lines: ", self.covered_lines)
            all_lines = ""
            for i, line in enumerate(file.read().split("\n"), start=1):
                all_lines += f"{i}. {line}" + "\n"
                if i in self.covered_lines:
                    self._covered_lines_dict[i] = line
                elif i in self.missing_lines:
                    self._miss_lines_dict[i] = line

    def print_lines(self, line_type: str = "covered"):
        lines_dict = (
            self._covered_lines_dict
            if line_type == "covered"
            else self._miss_lines_dict
        )
        # if not lines_dict:
        #     raise Exception(f"Need to run read_line_contents first")

        repr = ""
        repr += f"{line_type} lines in :: {self.filename}\n"
        for k, v in lines_dict.items():
            repr += f"{k}: {v}\n"

        return repr

    def get_contiguous_lines(self) -> Iterable[List[Tuple[int, str]]]:
        """
        Returns a list of contiguous line groups
        """
        from itertools import groupby

        for k, g in groupby(
            enumerate(self._covered_lines_dict.items()), lambda ix: ix[1][0] - ix[0]
        ):
            yield [x for _, x in g]

    def serialize(self):
        return {
            "filename": self.filename,
            "covered_lines": self.covered_lines,
            "missing_lines": self.missing_lines,
        }

    @classmethod
    def deserialize(self, data) -> "Coverage":
        return Coverage(data["filename"], data["covered_lines"], data["missing_lines"])


class NoCoverageDB(Exception):
    pass


class TestCoverage:
    """
    Coverage for a list of files from a commit
    """

    def __init__(
        self,
        cov_list: List[Coverage],
        isdiff: bool = False,
    ):
        self.isdiff = isdiff
        self._cov_list = cov_list

        total_misses = 0
        total_stmts = 0
        total_covered = 0
        for coverage in cov_list:
            total_misses += coverage.misses
            total_stmts += coverage.stmts
            total_covered += coverage.covered

        self.total_cov = Coverage("TOTAL", [], [])
        self.total_cov.misses = total_misses
        self.total_cov.stmts = total_stmts
        self.total_cov.covered = total_covered

    @property
    def cov_list(self):
        return [cov for cov in self._cov_list if cov.filename != "TOTAL"]

    # REFACTOR-RUNNER: re-implement as a mixin-method on TestCoverage
    @classmethod
    def from_coverage_file(cls, coverage_json: dict) -> "TestCoverage":
        cov_list = []

        if not coverage_json:
            return cls(cov_list)

        # # add exception catcher here for missing json
        for filename, data in coverage_json["files"].items():
            cov_list.append(
                Coverage(
                    filename,
                    data["executed_lines"],
                    data["missing_lines"] + data["excluded_lines"],
                )
            )

        return cls(cov_list)

    @classmethod
    def diff_cov(
        cls, a: "TestCoverage", b: "TestCoverage", keep_line: int
    ) -> "TestCoverage":
        """
        Used for subtracting two TestCoverages when we also want to diff their covered_lines
        keep_line parameter is introduced to control the order of the set subtraction
        """
        if keep_line not in [1, 2]:
            raise ValueError("keep_line must be 1 or 2")

        cov_list = []
        for a, b in zip(a.cov_list, b.cov_list):
            cov_diff = Coverage.diff_cov(a, b, keep_line)
            cov_list.append(cov_diff)

        return cls(cov_list, isdiff=True)

    def get_file_cov(self, filename: Path, base_path: Path) -> Optional[Coverage]:
        """
        Gets a file coverage by filename. Base_path required because coverage file paths are relative
        to the repo_path as root
        """
        try:
            cov = next(
                filter(
                    lambda x: (
                        x.filename == filename
                        if not base_path
                        else base_path / x.filename == filename
                    ),
                    self.cov_list,
                )
            )
            return cov
        except StopIteration:
            return None
        
    # def get_file_cov(self, filename: Path, base_path: Path) -> Optional[Coverage]:
    #     """
    #     Gets a file coverage by filename. Base_path required because coverage file paths are relative
    #     to the repo_path as root
    #     """
    #     try:
    #         return next(
    #             filter(
    #                 lambda x: (
    #                     x.filename
    #                     if not base_path
    #                     else base_path / x.filename == filename
    #                 ),
    #                 self.cov_list,
    #             )
    #         )
    #     except StopIteration:
    #         return None
        
    def read_line_coverage(self, base_path: Path):
        """
        Lazily reads the line contents of the file
        """
        for cov in self.cov_list:
            cov.read_line_contents(base_path)

    def print_lines(self):
        return "\n".join([cov.print_lines() for cov in self.cov_list])
    
    def __bool__(self):
        return self.cov_list != []

    def __iter__(self):
        return iter([cov for cov in self.cov_list if cov.filename != "TOTAL"])

    def is_zero(self):
        return self.total_cov.misses == 0

    def __sub__(self, other: "TestCoverage") -> "TestCoverage":
        """
        Take the difference of every matching file coverage plus our own coverage
        that is not matched by other and that is nonzero
        """
        a, b = self.cov_list, other.cov_list

        merged_list = []
        a_only_cov = [a for a in a if a.filename not in [b.filename for b in b]]
        intersect_fp = [i.filename for i in a if i.filename in [b.filename for b in b]]

        for cov_a in a:
            for cov_b in b:
                if cov_a.filename == cov_b.filename and cov_a.filename in intersect_fp:
                    cov_diff = cov_a - cov_b
                    if cov_diff.covered != 0:
                        merged_list.append(cov_diff)

        return TestCoverage(merged_list + a_only_cov, isdiff=True)

    def __add__(self, other: Union["TestCoverage", Coverage]) -> "TestCoverage":
        """
        Take add to our existing coverage only those lines that are not covered by ours
        """
        if isinstance(other, Coverage):
            other = TestCoverage([other], isdiff=True)

        if not self.isdiff:
            raise Exception("Can only add coverage for TestCoverage.isdiff == True") 

        a, b = self.cov_list, other.cov_list
        merged_list = []

        intersect_files = [i.filename for i in a if i.filename in [b.filename for b in b]]
        a_only_cov = [a for a in a if a.filename not in intersect_files]
        b_only_cov = [b for b in b if b.filename not in intersect_files]

        for cov_a, cov_b in product(a, b):
            if cov_a.filename == cov_b.filename and cov_a.filename in intersect_files:
                merged_list.append(cov_a + cov_b)

        return TestCoverage(a_only_cov + merged_list + b_only_cov, isdiff=True)
    
    def __eq__(self, other: "TestCoverage") -> bool:
        for cov in self.cov_list:
            if cov.filename == "TOTAL":
                continue
            if cov not in other.cov_list:
                return False

        return True

    # NOTE: this should be the official API for adding TestCoverage
    def add_coverage(self, other: "TestCoverage"):
        if not self.isdiff:
            raise Exception("Can only add coverage for TestCoverage.isdiff == True") 
        
        return self.__add__(other)

    def get_covered(self, other: "TestCoverage") -> int:
        """
        Returns an integer indicating how lines in other that is also in self
        """
        covered = 0

        for cov in other.cov_list:
            for self_cov in self.cov_list:
                if cov.filename == self_cov.filename:
                    missing_lines = set(cov.covered_lines) - set(self_cov.covered_lines)
                    covered += len(cov.covered_lines) - len(missing_lines)

        return covered 
        
    def covered_lines(self) -> List[Tuple[str, List[int]]]:
        cov_lines = [(cov.filename, cov.covered_lines) for cov in self.cov_list]
        return cov_lines

    def missing_lines(self) -> List[Tuple[str, List[int]]]:
        cov_lines = [(cov.filename, cov.missing_lines) for cov in self.cov_list]
        return cov_lines

    def cov_list_str(self):
        return "\n".join([str(cov) for cov in self.cov_list])

    def __repr__(self):
        return f"TestCoverage: {self.total_cov}, IsDiff:{self.isdiff}"

    def serialize(self):
        return {
            "cov_list": [cov.serialize() for cov in self.cov_list],
            "isdiff": self.isdiff,
        }

    @classmethod
    def deserialize(cls, data: List[List]) -> "TestCoverage":
        return cls(
            [Coverage(**lines) for lines in data["cov_list"]],
            isdiff=data["isdiff"],
        )


TestError = NewType("TestError", str)


class CoverageResult:
    """
    Represents the result of a coverage run
    """

    def __init__(self, stdout: str, stderr: str, coverage_json: Dict):
        self.coverage: TestCoverage = TestCoverage.from_coverage_file(coverage_json)
        # self.coverage2 = TestCoverage.from_coverage_report(stdout)

        self.total_tests = self._parse_total_tests(stdout)
        self.failed, self.total_failed = self._parse_failed_tests(stdout)
        self.stderr = stderr
        # generated functions
        self.gen_funcs = []

    def to_dict(self) -> Dict:
        return {"coverage": self.coverage.serialize(), "failed": self.failed}

    def _parse_total_tests(self, stdout: str):
        """
        Parse total number of tests from pytest output
        """
        pattern = r"collected\s+(\d+)\s+items"
        match = re.search(pattern, stdout)
        if match:
            return int(match.group(1))
        return 0

    # TODO: parse pytest errors as well as failure
    def _parse_failed_tests(
        self, stdout: str
    ) -> Tuple[List[Tuple[str, TestError]], int]:
        """
        Parse every failed test from pytest output
        """
        pattern = r"FAILED\s+(?:\S+?)::(\S+?)\s+-"
        failed_modules = re.findall(pattern, stdout)

        # NOTE: currently treating parameterized tests as single tests
        total_failed = set()

        # parse test_module names
        for failed_test in failed_modules:
            # logger.info(f"Failed tests: {failed_test}")

            if "[" in failed_test:
                failed_test = failed_test.split("[")[0]

            if "::" in failed_test:
                test_module = failed_test.split("::")[0]
                failed_test = failed_test.split("::")[1]
                total_failed.add(f"{test_module}.{failed_test}")

            total_failed.add(failed_test)

        logger.info(f"Total failed tests: {len(failed_modules)}")

        # parse error info
        pattern = r"_{2,}(\s+\b[\w\.]+)(?:\[\S+\])?\s+_{2,}\n(.*?)\n[_|-]"
        test_info = re.findall(pattern, stdout, re.DOTALL)

        return {f.strip(): error.rstrip() for f, error in test_info}, len(total_failed)

    def get_failed(self, test_name):
        """
        Did test_name fail in this coverage run?
        """
        return self.failed.get(test_name, None)

    def __bool__(self):
        return bool(self.coverage)

    def get_coverage(self):
        return self.coverage

    # actually parse out the stderr
    def get_error(self):
        if not self.stderr:
            raise Exception("No error found")
        return self.stderr
