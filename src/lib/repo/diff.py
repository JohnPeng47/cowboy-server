from src.lib.utils import find_substring

from typing import List, Tuple, Optional, NewType, NamedTuple
from pathlib import Path
import re
from enum import Enum

SHA = NewType("SHA", str)


class NoTestCtxtException(Exception):
    pass


class HunkChunk:
    """
    A hunk in a diff
    """

    def __init__(self, body: str):
        self.body = body

        lines = self.body.split("\n")
        o_start, o_end, n_start, n_end = self._parse_hunk_header(lines[0])
        self.old_range = (o_start, o_end)
        self.new_range = (n_start, n_end)

        self.plus_blob, self.minus_blob = self._parse_hunk_lines(body)
        self.new_func = self._new_func_decl()

    def _parse_hunk_lines(self, body: str) -> Tuple[List[str], List[str]]:
        """
        Parses a hunk in a diff
        """
        plus_lines = []
        minus_lines = []
        for line in body.split("\n"):
            if line.startswith("+"):
                plus_lines.append(line[1:])
            elif line.startswith("-"):
                minus_lines.append(line[1:])

        return "\n".join(plus_lines), "\n".join(minus_lines)

    def _parse_hunk_header(self, line: str) -> Optional[Tuple[int, int]]:
        """
        Returns the line number of the hunk
        """
        pattern = r"@@ -(\d+),?(\d+)? \+(\d+),?(\d+)? @@"

        # Use regex to find matches in the hunk
        match = re.search(pattern, line)

        def convert_to_int(matched):
            if matched:
                return int(matched)
            if matched is None:
                return -1

        if match:
            old_start, old_count, new_start, new_count = map(
                convert_to_int, match.groups()
            )
            return old_start, old_start + old_count, new_start, new_start + new_count

        return None, None, None, None

    def _new_func_decl(self) -> str:
        """
        If the hunk declares a new test function, return it
        """
        # Hunk can be empty since we are only currently looking at + lines
        # if len(self.lines) == 0:
        #     return ""

        PYTHON_FUN_DEF = r"\+?\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\("
        match = re.search(PYTHON_FUN_DEF, self.body)
        if match:
            return match.group(1)
        else:
            return ""


class DiffMode(Enum):
    MODIFIED = "modified"
    DELETED = "deleted"
    NEW = "new"
    UNKNOWN = "unknown"


class DiffAttr(NamedTuple):
    a_path: str
    b_path: Optional[str]
    b_path_fallback: str  # have no idea wtf this thing is
    mode: DiffMode


class Diff:
    def __init__(self, body: str):
        self.body = body
        self.attrs: DiffAttr = self._parse_patch_attributes()
        self.hunks: List[HunkChunk] = self._parse_hunks()
        # lets assume this is the most reliable path, because it *should* account
        # for new/renamed files
        # remove b/ from begining
        self.filepath: str = self._find_new_filepath()

    def _find_new_filepath(self) -> str:
        """
        Finds the filepath of the b/file
        """
        if self.attrs:
            return self.norm_path(self.attrs.b_path_fallback)

        # look for the +++ line
        for line in self.body.split("\n"):
            if line.startswith("+++"):
                return line[3:].strip()

    def norm_path(self, path: str) -> str:
        """
        Removes the "a/" and "b/" prefixes
        """
        return path[2:]

    def _parse_hunks(self) -> List[HunkChunk]:
        hunks = []
        hunk_starts = find_substring(self.body, "@@")

        try:
            start = hunk_starts.pop(0)
        except IndexError:
            return []

        for end in hunk_starts:
            hunk_body = self.body[start:end]
            start = end
            hunks.append(HunkChunk(hunk_body))
        hunks.append(HunkChunk(self.body[start:]))  # last hunk

        return hunks

    def _parse_patch_attributes(self) -> DiffAttr:
        """
        Stolen from GitPython (properly attribute later)
        """
        re_header = re.compile(
            rb"""
                                    ^diff[ ]--git
                                        [ ](?P<a_path_fallback>"?[ab]/.+?"?)[ ](?P<b_path_fallback>"?[ab]/.+?"?)\n
                                    (?:^old[ ]mode[ ](?P<old_mode>\d+)\n
                                    ^new[ ]mode[ ](?P<new_mode>\d+)(?:\n|$))?
                                    (?:^similarity[ ]index[ ]\d+%\n
                                    ^rename[ ]from[ ](?P<rename_from>.*)\n
                                    ^rename[ ]to[ ](?P<rename_to>.*)(?:\n|$))?
                                    (?:^new[ ]file[ ]mode[ ](?P<new_file_mode>.+)(?:\n|$))?
                                    (?:^deleted[ ]file[ ]mode[ ](?P<deleted_file_mode>.+)(?:\n|$))?
                                    (?:^similarity[ ]index[ ]\d+%\n
                                    ^copy[ ]from[ ].*\n
                                    ^copy[ ]to[ ](?P<copied_file_name>.*)(?:\n|$))?
                                    (?:^index[ ](?P<a_blob_id>[0-9A-Fa-f]+)
                                        \.\.(?P<b_blob_id>[0-9A-Fa-f]+)[ ]?(?P<b_mode>.+)?(?:\n|$))?
                                    (?:^---[ ](?P<a_path>[^\t\n\r\f\v]*)[\t\r\f\v]*(?:\n|$))?
                                    (?:^\+\+\+[ ](?P<b_path>[^\t\n\r\f\v]*)[\t\r\f\v]*(?:\n|$))?
                                """,
            re.VERBOSE | re.MULTILINE,
        )

        diff_attrs = []

        try:
            # Encode normally, expecting no surrogates
            encoded_body = bytes(self.body, encoding="utf-8")
        except UnicodeEncodeError:
            # Handle the presence of surrogates explicitly
            encoded_body = bytes(self.body, encoding="utf-8", errors="surrogateescape")

        for _header in re_header.finditer(encoded_body):
            (
                a_path_fallback,
                b_path_fallback,
                old_mode,
                new_mode,
                rename_from,
                rename_to,
                new_file_mode,
                deleted_file_mode,
                copied_file_name,
                a_blob_id,
                b_blob_id,
                b_mode,
                a_path,
                b_path,
            ) = _header.groups()

            a_path = self.norm_path(a_path) if a_path else b""
            b_path = self.norm_path(b_path) if b_path else b""
            file_mode = None

            if new_file_mode:
                file_mode = DiffMode.NEW
            elif deleted_file_mode:
                file_mode = DiffMode.DELETED
            elif a_path and b_path and a_path == b_path:
                file_mode = DiffMode.MODIFIED
            else:
                file_mode = DiffMode.UNKNOWN

            diff_attrs.append(
                DiffAttr(
                    a_path.decode("utf-8"),
                    b_path.decode("utf-8"),
                    b_path_fallback.decode("utf-8") if b_path_fallback else "",
                    file_mode,
                )
            )
        # at this point we've already split the diff into sections
        return diff_attrs[0] if len(diff_attrs) > 0 else []

    def __str__(self):
        return self.body


class DiffsNotFoundException(Exception):
    pass


# this class needs a rewrite ...
# TODO: add file mode to each diff chunk
class CommitDiff:
    """
    Class to represent a diff/patch

    FYI patch is a diff that can be applied directly to a filepath
    """

    # TODO: Too much logic in the __init__ method, move inside methods instead
    def __init__(
        self,
        patch: str,
        timestamp: str = None,
    ):
        if not patch:
            raise DiffsNotFoundException("Empty patch file argument")
        try:
            self.diffs = self._segment_diffs(patch)
            self.files = [d.filepath for d in self.diffs]
            self.hunks = [hunk for d in self.diffs for hunk in d.hunks]
            self._timestamp = timestamp
        except Exception as e:
            print(f"Patch parsing error:\n{e}")
            print(f"Patch:\n{patch}")

    def code_diffs(self):
        return [diff for diff in self.diffs if self.is_code_file(diff.filepath)]

    def is_code_file(self, filename: str):
        return "test" not in filename and filename.endswith(".py")

    def is_test_file(self, filename: str):
        return "test" in filename and filename.endswith(".py")

    @property
    def timestamp(self) -> str:
        return getattr(self, "_timestamp", None)

    def find_diff(self, filename: str) -> Optional[Diff]:
        """
        Returns a diff corresponding to the filename
        """
        for diff in self.diffs:
            if Path(diff.filepath) == Path(filename):
                return diff
        return None

    # @property
    # def code_diff(self) -> str:
    #     """
    #     All diffs pertaining to non-test case files joined together
    #     """
    #     diff = "\n".join(
    #         [diff.body for diff in self.diffs if diff.filepath not in self.test_files]
    #     )
    #     if diff:
    #         return diff + "\n"
    #     # not sure
    #     else:
    #         return ""

    # @property
    # def tests_diff(self) -> str:
    #     """
    #     All diffs pertaining to pytest unit test cases joined together
    #     """
    #     diff = "\n".join(
    #         [diff.body for diff in self.diffs if diff.filepath in self.test_files]
    #     )
    #     if diff:
    #         return diff + "\n"
    #     else:
    #         return ""

    # def __str__(self):
    #     return self.code_diff + "\n" + self.tests_diff

    @property
    def test_files(self) -> List[str]:
        return [d.filepath for d in self.diffs if self.is_test_file(d.filepath)]

    @property
    def code_files(self) -> List[str]:
        return [d.filepath for d in self.diffs if self.is_code_file(d.filepath)]

    def _segment_diffs(self, patch: str) -> List[Diff]:
        """
        Segments the patch into diffs, where each diff marks whether a file has been
        modified, created anew, or deleted
        """

        diff_sections = []
        diff_starts = find_substring(patch, "diff --git")
        if not diff_starts:
            diff_starts = find_substring(patch, "---")

        try:
            start = diff_starts.pop(0)
        except IndexError:
            raise DiffsNotFoundException("No diff sections found in patch")

        for end in diff_starts:
            diff_sections.append(patch[start:end])
            start = end
        diff_sections.append(patch[start:])

        try:
            return [Diff(lines) for lines in diff_sections]
        except Exception as e:
            import traceback

            print(f"Error parsing diff:\n{e}")
            traceback.print_exc()
