from pathlib import Path

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import uuid4
from enum import Enum

from queue import Queue

import os
import subprocess
from typing import List, Tuple, NewType, Dict
import time
import re
import json

from src.run_config import RepoRunConfig
from src.coverage import TestCoverage
from src.db.cache import CacheRepository, Cache
from src.repo.repository import PatchFileContext, PatchFile
from src.repo.repository import GitRepo
from src.ast.code import Function
import hashlib

from pathlib import Path
from logging import getLogger


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass
class Task:
    """
    Database task, tied to a parent job.
    """

    task_id: str = str(uuid4())
    result: dict = dict()
    task_args: dict = dict()
    status: str = TaskStatus.PENDING.value
    name: str = ""


logger = getLogger("test_results")
longterm_logger = getLogger("longterm")

COVERAGE_FILE = "coverage.json"
TestError = NewType("TestError", str)


class DiffFileCreation(Exception):
    pass


def hash_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def hash_file(filepath):
    """Compute SHA-256 hash of the specified file"""
    with open(filepath, "r", encoding="utf-8") as f:
        buf = f.read()

    return hash_str(buf)


def hash_coverage_inputs(directory: Path, cmd_str: str) -> str:
    """Compute SHA-256 for the curr dir and cmd_str"""
    hashes = []
    for f in directory.iterdir():
        if f.is_file() and f.name.endswith(".py"):
            file_hash = hash_file(f)
            hashes.append((str(f), file_hash))

    # Sort based on file path and then combine the file hashes
    hashes.sort()
    combined_hash = hashlib.sha256()
    for _, file_hash in hashes:
        combined_hash.update(file_hash.encode())

    combined_hash.update(cmd_str.encode())
    return combined_hash.hexdigest()


class CoverageResult:
    """
    Represents the result of a coverage run
    """

    def __init__(self, stdout: str, stderr: str, coverage_json: Dict):
        self.coverage: TestCoverage = TestCoverage.from_coverage_file(coverage_json)
        # self.coverage2 = TestCoverage.from_coverage_report(stdout)

        self.failed: Dict[str, TestError] = self._parse_failed_tests(stdout)
        self.stderr = stderr
        # generated functions
        self.gen_funcs = []

    # TODO: we should parse errors as well
    def _parse_failed_tests(
        self, stdout: str, generated_tests: List[str] = []
    ) -> List[Tuple[str, TestError]]:
        """
        Parse every failed test from pytest output
        """
        pattern = r"FAILED\s+(?:\S+?)::(\S+?)\s+-"
        failed_modules = re.findall(pattern, stdout)

        # NOTE: currently treating parameterized tests as single tests
        total_failed_tests = set()

        # parse test_module names
        for failed_test in failed_modules:
            # logger.info(f"Failed tests: {failed_test}")

            if "[" in failed_test:
                failed_test = failed_test.split("[")[0]

            if "::" in failed_test:
                test_module = failed_test.split("::")[0]
                failed_test = failed_test.split("::")[1]
                total_failed_tests.add(f"{test_module}.{failed_test}")

            total_failed_tests.add(failed_test)

        logger.info(f"Total failed tests: {len(failed_modules)}")

        # parse error info
        pattern = r"_{2,}(\s+\b[\w\.]+)(?:\[\S+\])?\s+_{2,}\n(.*?)\n[_|-]"
        test_info = re.findall(pattern, stdout, re.DOTALL)

        return {f.strip(): error.rstrip() for f, error in test_info}

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


from contextlib import contextmanager
import queue


class LockedRepos:
    """
    A list of available repos for concurrent run_test invocations, managed as a FIFO queue
    """

    def __init__(self, path_n_git: List[Tuple[Path, GitRepo]]):
        self.queue = queue.Queue()
        for item in path_n_git:
            self.queue.put(item)

    @contextmanager
    def acquire_one(self) -> Tuple[Path, GitRepo]:
        path, git_repo = self.queue.get()  # This will block if the queue is empty
        logger.info(f"Acquiring repo: {path.name}")
        try:
            yield (path, git_repo)
        finally:
            self.release((path, git_repo))

    def release(self, path_n_git: Tuple[Path, GitRepo]):
        logger.info(f"Releasing repo: {path_n_git[0].name}")
        self.queue.put(path_n_git)  # Return the repo back to the queue

    def __len__(self):
        return self.queue.qsize()


def get_exclude_path(
    func: Function,
    rel_fp: Path,
):
    """
    Converts a Function path
    """
    excl_name = (
        (func.name.split(".")[0] + "::" + func.name.split(".")[1])
        if func.is_meth()
        else func.name
    )

    # need to do this on windows
    return str(rel_fp).replace("\\", "/") + "::" + excl_name


class PytestDiffRunner:
    """
    Executes the test suite before and after a diff is applied,
    and compares the results. Runs in two modes: full and selective.
    In full mode, the full test suite is run.
    In selective mode, only selected test cases.
    """

    def __init__(
        self,
        # assume to be a test file for now
        run_config: RepoRunConfig,
        test_suite: str = "",
        cache_db: CacheRepository = None,
        cloned_dirs: List[Path] = [],
        generated_tests: List[str] = [],
    ):
        self.cache_db = cache_db
        if not self.cache_db:
            logger.warning("Not using cache for runner")

        # prolly just better to not alias repo.var here
        self.src_folder = run_config.src_folder
        self.test_folder = run_config.test_folder
        self.cov_folders = run_config.cov_folders
        self.repoconf_folder = run_config.repoconf_folder
        self.repo_path = run_config.repo_path
        self.interpreter = run_config.interp
        self.python_path = run_config.python_path

        self.test_repos = LockedRepos(
            list(zip(cloned_dirs, [GitRepo(p) for p in cloned_dirs]))
        )
        if len(self.test_repos) == 0:
            raise Exception("No testrepos for runner")

        if not self.src_folder.exists():
            # false positive here for: 'C:\\Users\\jpeng\\Documents\\business\\auto_test\\repos\\trio\\src\\trio'
            # raise Exception("src folder does not exist: ", os.path.abspath(src_path))
            logger.warning(f"src folder does not exist: {self.src_folder.resolve()}")

        self.test_suite = test_suite

    def verify_clone_dirs(self, cloned_dirs):
        """
        Checks that each cloned dir is in the same state as the others
        """
        # commit = get_current_git_commit(cloned_dirs[0])
        # for clone in cloned_dirs[1:]:
        #     if get_current_git_commit(clone) != commit:
        #         raise Exception(f"{clone} have a different commit")
        import hashlib

        for clone in cloned_dirs:
            f_buf = ""
            for py_file in clone.glob("test*.py"):
                with open(py_file, "r") as f:
                    f_buf += f.read()

            f_buf_hash = hashlib.md5(f_buf.encode()).hexdigest()
            print(f"Hash for {clone}: ", f_buf_hash)

    def set_test_repos(self, repo_paths: List[Path]):
        self.test_repos = LockedRepos(
            list(zip(repo_paths, [GitRepo(p) for p in repo_paths]))
        )

        self.verify_clone_dirs(repo_paths)

    def _get_exclude_tests_arg_str(
        self, excluded_tests: List[Tuple[Function, Path]], cloned_path: Path
    ):
        """
        Convert the excluded tests into Pytest deselect args
        """
        if not excluded_tests:
            return ""

        tranf_paths = []
        for test, test_fp in excluded_tests:
            # find the common shared folder
            rel_path = test_fp.parts[len(cloned_path.parts) - 1 :]
            tranf_paths.append(get_exclude_path(test, Path(*rel_path)))

        return "--deselect=" + " --deselect=".join(tranf_paths)

    def _get_include_tests_arg_str(self, excluded_tests: []):
        if not excluded_tests:
            return ""

        arg_str = ""
        AND = " and"
        for test in excluded_tests:
            arg_str += f"{test}{AND}"

        arg_str = arg_str[: -len(AND)]
        # return "-k " + '"' + arg_str + '"'
        return "-k " + arg_str

    def _construct_cmd(
        self, repo_path, selected_tests: str = "", deselected_tests: str = ""
    ):
        """
        Constructs the cmdstr for running pytest
        """

        cmd = [
            "cd",
            str(repo_path),
            "&&",
            str(self.interpreter.resolve()),
            "-m",
            "pytest",
            str(self.test_folder.name),
            "--tb",
            "short",
            selected_tests,
            deselected_tests,
            # "-v",
            "--color",
            "no",
            # "-ra",
            # fails for request
            # "--timeout=30",
            # "--cov-report html",
            f"--cov={'--cov='.join([str(folder) + ' ' for folder in self.cov_folders])}",
            "--cov-report",
            "json",
            "--cov-report",
            "term",
            "--continue-on-collection-errors",
            "--disable-warnings",
        ]

        return " ".join(cmd)

    from contextlib import contextmanager

    ### CAREFUL: IF WE ARE TO USE THIS IN THE FUTURE, WE NEED TO MAKE CORRESPONDING CHANGES
    ### TO THE CACHE IMPLEMENTATION TO TAKE THE CONTENTS OF PYTEST.INI INTO ACCOUNT
    ### may need for long azz commandlines
    # @contextmanager
    # def manage_pytest_ini(self):
    #     pytest_ini_path = self.test_folder / "pytest.ini"
    #     # if pytest_ini_path.exists():
    #     #     raise Exception(f"Pre-existing pytest.ini in {pytest_ini_path}")

    #     try:
    #         with open(pytest_ini_path, "w") as f:
    #             f.write("[pytest]\n")
    #             f.write("addopts = ")
    #             # Add any necessary pytest configurations here
    #             yield f
    #     finally:
    #         os.remove(pytest_ini_path)

    def run_test(
        self,
        exclude_tests: List[Tuple[Function, Path]] = [],
        include_tests: List[str] = [],
        patch_file: PatchFile = None,
        git_repo: GitRepo = None,
        cache=False,
    ) -> Tuple[CoverageResult, str, str]:
        with self.test_repos.acquire_one() as repo_inst:
            cloned_path, git_repo = repo_inst

            env = os.environ.copy()
            if self.python_path:
                env["PYTHONPATH"] = self.python_path

            exclude_tests = self._get_exclude_tests_arg_str(exclude_tests, cloned_path)
            include_tests = self._get_include_tests_arg_str(include_tests)
            cmd_str = self._construct_cmd(cloned_path, include_tests, exclude_tests)

            logger.debug(f"Running with command::")
            print(f"Cmd: {cmd_str}")
            with PatchFileContext(git_repo, patch_file):
                proc = subprocess.Popen(
                    cmd_str,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    text=True,
                )
                stdout, stderr = proc.communicate()
                if stderr:
                    logger.info(f"Stderr: {stderr}")

                # we want
                if cache and self.cache_db:
                    # problem with this is it doesnt take into account test deselection that affects coverage
                    key = hash_coverage_inputs(cloned_path, cmd_str)
                    cached_value = self.cache_db.get_one(key)
                    if cached_value:
                        stdout, stderr, coverage_json = (
                            cached_value.data["stdout"],
                            cached_value.data["stderr"],
                            cached_value.data["coverage_json"],
                        )

                        # TODO: remove this, we actually dont need it
                        # ERROR: potential big fail here if coverage.json is not synced up
                        cov = CoverageResult(stdout, stderr, coverage_json)
                        logger.info(f"Getting cached coverage value...")
                        logger.debug(f"Using cache key: {key}")
                        return (
                            cov,
                            stdout,
                            stderr,
                        )
                    elif stdout:
                        logger.warning("Saving stdout/stderr to cache")
                        self.cache_db.set(
                            Cache(
                                key=key,
                                data={
                                    "stdout": stdout,
                                    "stderr": stderr,
                                    "coverage_json": coverage_json,
                                },
                            )
                        )

                # read coverage
                with open(cloned_path / COVERAGE_FILE, "r") as f:
                    coverage_json = json.loads(f.read())
                    cov = CoverageResult(stdout, stderr, coverage_json)

            # logger.info(f"Stdout: {stdout}")
            # Dont think all errors are captured here
            # ie. The error section of textual, without msgpack import

        return (
            cov,
            stdout,
            stderr,
        )
