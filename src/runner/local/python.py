from src.lib.ast import Function, Class, NodeType
from src.lib.repo.repository import PatchFile, PatchFileContext, GitRepo
from src.lib.coverage import CoverageResult
from src.lib.api.runner.shared import RunTestTaskArgs, FunctionArg
from src.lib.test_modules import TestModule

from src.logger import testgen_logger, buildtm_logger, MultiLogger

from .models import RepoConfig

from io import StringIO
import configparser
import os
import subprocess
from typing import List, Tuple, NewType, Dict, Set
import json
import hashlib
from pathlib import Path
import time
import sys
from contextlib import contextmanager
import queue

log = MultiLogger(testgen_logger, buildtm_logger)
COVERAGE_FILE = "coverage.json"
TestError = NewType("TestError", str)


class RunnerError(Exception):
    pass

class DiffFileCreation(Exception):
    pass

class CowboyClientError(Exception):
    pass

class TestSuiteError(Exception):
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

def update_coverage_omits(filepath: str = ".coveragerc") -> str:
    """
    Update .coveragerc file to include standard omit patterns in the [run] section.
    Creates the omit section if it doesn't exist. Creates the file if it doesn't exist.
    
    Args:
        filepath (str): Path to the .coveragerc file
    
    Returns:
        str: The updated configuration as a string
    """
    DEFAULT_OMITS = [
        ".env/*",
        "build/*",
        "dist/*", 
        "venv/*",
        "tests/*",
        "*/tests/*",
        "test_*",
        "*_test.py"
    ]
    
    # Create empty file if it doesn't exist
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            f.write("")
    
    # Read existing config
    config = configparser.ConfigParser()
    config.read(filepath)
    
    # Ensure [run] section exists
    if "run" not in config:
        config["run"] = {}
    
    # Get current omits if they exist
    current_omits: Set[str] = set()
    if "omit" in config["run"]:
        # Handle multiline omit values
        omit_str = config["run"]["omit"].strip()
        if omit_str:
            # Split by commas and/or newlines, strip whitespace and filter empty strings
            current_omits = {
                item.strip() for item in omit_str.replace("\n", ",").split(",")
                if item.strip()
            }
    
    # Add new omits
    updated_omits = current_omits.union(DEFAULT_OMITS)
    
    # Format the omit string with each pattern on a new line
    formatted_omits = "\n    ".join(sorted(updated_omits))
    config["run"]["omit"] = f"\n    {formatted_omits}"
    
    output = StringIO()
    config.write(output)
    return output.getvalue()

class LockedRepos:
    """
    A list of available repos for concurrent run_test invocations, managed as a FIFO queue
    """

    def __init__(self, cloned_folders: List[Path]):
        self.capacity = len(cloned_folders)
        self.queue = queue.Queue()

        for path in cloned_folders:
            if not path.exists():
                raise RunnerError(
                    f"Cloned folder: {str(path)} does not exist, something went wrong. Try deleting and re-creating the repo"
                )

            self.queue.put(GitRepo(path))

    @contextmanager
    def acquire_one(self) -> GitRepo:
        git_repo: GitRepo = self.queue.get()  # This will block if the queue is empty

        log.info(f"Acquired repo: {git_repo.repo_folder}")
        try:
            yield git_repo
        finally:
            self.release(git_repo)

            log.info(f"Released repo: {git_repo.repo_folder}")

    def release(self, git_repo: GitRepo):
        self.queue.put(git_repo)  # Return the repo back to the queue

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

    # fucking pytest syntax is so dumb
    # if func.is_meth():
    #     return str(rel_fp).replace("\\","/") + func.name.split(".")[0] + "::" + func.name.split(".")[1]
    # else:
    #     return str(rel_fp.name).replace("\\", "/") + "::" + func.name


class PytestDiffRunner:
    """
    Executes the test suite
    """
    def __init__(
        self,
        # assume to be a test file for now
        repo_conf: RepoConfig,
        test_suite: str = "",
    ):
        self.test_folder = Path(repo_conf.python_conf.test_folder)
        self.interpreter = Path(repo_conf.python_conf.interp)
        self.python_path = Path(repo_conf.python_conf.pythonpath)

        # if not self.interpreter.exists():
        #     raise RunnerError(f"Runtime path {self.interpreter} does not exist")

        # missing = self.check_missing_deps(self.interpreter)
        # if missing:
        #     raise RunnerError(f"{missing} for {self.interpreter}")

        self.cov_folders = [Path(p) for p in repo_conf.python_conf.cov_folders]
        cloned_folders = [Path(p) for p in repo_conf.cloned_folders]
        self.test_repos = LockedRepos(cloned_folders)

        if len(self.test_repos) == 0:
            raise CowboyClientError("No cloned repos created, perhaps run init again?")

        self.test_suite = test_suite

    def check_missing_deps(self, interp) -> List[bool]:
        """
        Check if test depdencies are installed in the interpreter
        """
        not_installed = []
        deps = ["pytest-cov", "pytest"]
        try:
            for dep in deps:
                result = subprocess.run(
                    [interp, "-m", "pip", "show", dep],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    not_installed.append(dep)

        except (subprocess.CalledProcessError, FileNotFoundError):
            not_installed.append(dep)

        return (
            f"The following deps are not installed in the env: {not_installed}\nPlease install these"
            if not_installed
            else ""
        )

    def verify_clone_dirs(self, cloned_dirs: List[Path]):
        """
        Verifies that the hash of all *.py files are the same for each cloned dir
        """
        import hashlib

        hashes = []
        for clone in cloned_dirs:
            f_buf = ""
            for py_file in clone.glob("test*.py"):
                with open(py_file, "r") as f:
                    f_buf += f.read()

            f_buf_hash = hashlib.md5(f_buf.encode()).hexdigest()
            hashes.append(f_buf_hash)

        if any(h != hashes[0] for h in hashes):
            raise CowboyClientError("Cloned directories are not the same")

    def set_test_repos(self, repo_paths: List[Path]):
        self.test_repos = LockedRepos(
            list(zip(repo_paths, [GitRepo(p) for p in repo_paths]))
        )

        self.verify_clone_dirs(repo_paths)

    def _get_test_args(
        self,
        include_tm: TestModule = None,
        excluded_tests: List[Tuple[Function, Path]] = None,
        cloned_path: Path = None
    ) -> Tuple[str, str, str]:
        """
        Get pytest test selection arguments for both including and excluding tests
        
        Returns:
            Tuple of (selected_tests, deselected_tests, test_file)
        """
        # Handle excluded tests
        deselected_tests = ""
        if excluded_tests:
            tranf_paths = []
            for test, test_fp in excluded_tests:
                tranf_paths.append(get_exclude_path(test, test_fp))
            deselected_tests = "--deselect=" + " --deselect=".join(tranf_paths)

        # Handle included tests
        selected_tests = ""
        test_file = ""
        if include_tm:
            # Only add -k flag if not a .py file
            # This change allows running specific test files without filtering by name
            if not deselected_tests:
                selected_tests = "-k " + include_tm.name
            test_file = include_tm.test_file.path

        return selected_tests, deselected_tests, test_file
    
    def _get_coveragerc(self, base_path: Path) -> str:
        """Returns a .coveragerc file that omits test file patterns along with the original content"""
        return update_coverage_omits(base_path / ".coveragerc")
  
    def _construct_cmd(
        self, 
        repo_path: Path,  
        selected_tests: str, 
        deselected_tests: str,
        test_file: str = "",
        custom_cmd: str = ""
    ):
        """
        Constructs the cmdstr for running pytest
        """
        test_path = test_file if test_file else self.test_folder
        cd_cmd = [
            "cd",
            str(repo_path),
        ]

        if custom_cmd:
            cmd = custom_cmd
        else:
            cmd = [
                str(self.interpreter),
                "-m",
                "pytest",
                str(test_path),
                "--tb",
                "short",
                selected_tests,
                deselected_tests,
                # "-v",
                "--color",
                "no",
                f"--cov={'--cov='.join([str(folder) + ' ' for folder in self.cov_folders])}",
                "--cov-report",
                "json",
                # "--cov-report",
                # "term",
                "--continue-on-collection-errors",
                "--disable-warnings",
            ]

        return " ".join(cd_cmd + ["&&"] + cmd)

    def _stream_and_capture_output(self, process: subprocess.Popen) -> Tuple[str, str]:
        """
        Streams subprocess output to terminal while also capturing it in variables.
        
        Args:
            process: A subprocess.Popen instance with stdout and stderr as PIPE
            
        Returns:
            Tuple containing the captured stdout and stderr as strings
        """
        stdout_chunks = []
        stderr_chunks = []
        
        # Get file objects for stdout and stderr
        stdout_fd = process.stdout.fileno()
        stderr_fd = process.stderr.fileno()
        
        # Make stdout and stderr non-blocking
        os.set_blocking(stdout_fd, False)
        os.set_blocking(stderr_fd, False)
        
        while True:
            # Check if process has finished
            retcode = process.poll()
            
            # Try reading from stdout
            try:
                stdout_chunk = os.read(stdout_fd, 1024).decode('utf-8')
                if stdout_chunk:
                    print(stdout_chunk, end='', flush=True)
                    stdout_chunks.append(stdout_chunk)
            except (OSError, BlockingIOError):
                pass
                
            # Try reading from stderr
            try:
                stderr_chunk = os.read(stderr_fd, 1024).decode('utf-8')
                if stderr_chunk:
                    print(stderr_chunk, end='', flush=True, file=sys.stderr)
                    stderr_chunks.append(stderr_chunk)
            except (OSError, BlockingIOError):
                pass
                
            # If process has finished and no more output, break
            if retcode is not None and not stdout_chunk and not stderr_chunk:
                break
                
            # Small sleep to prevent CPU spinning
            time.sleep(0.1)
        
        return ''.join(stdout_chunks), ''.join(stderr_chunks)
        
    def run_testsuite(self, 
                      args: RunTestTaskArgs, 
                      stream: bool = False,
                      custom_cmd: str = "") -> Tuple[CoverageResult, str, str]:
        with self.test_repos.acquire_one() as repo_inst:
            git_repo: GitRepo = repo_inst

            patches = []
            patch_file = args.patch_file
            if patch_file:
                patch_file.path = git_repo.repo_folder / patch_file.path

            # write .coveragerc to exclude test files
            coverage_rc = self._get_coveragerc(git_repo.repo_folder)
            patches.append(PatchFile(
                path=git_repo.repo_folder / ".coveragerc", 
                patch=coverage_rc
            ))
            if patch_file:
                patches.append(patch_file)
                
            env = os.environ.copy()
            if self.python_path:
                env["PYTHONPATH"] = self.python_path

            selected_tests, deselected_tests, test_file = self._get_test_args(
                args.include_tests,
                args.exclude_tests,
                git_repo.repo_folder
            )
            cmd_str = self._construct_cmd(
                git_repo.repo_folder, selected_tests, deselected_tests, test_file=test_file, custom_cmd=custom_cmd
            )
            log.info(f"CMD: {cmd_str}")

            with PatchFileContext(git_repo, patches):
                proc = subprocess.Popen(
                    cmd_str,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    text=True,
                )
                if stream:
                    stdout, stderr = self._stream_and_capture_output(proc)
                else:
                    stdout, stderr = proc.communicate()

                # raise exception only no coverage
                try:
                    with open(git_repo.repo_folder / COVERAGE_FILE, "r") as f:
                        coverage_json = json.loads(f.read())
                        cov = CoverageResult(stdout, stderr, coverage_json)
                        if not cov.coverage:
                            print("No coverage!")
                            raise Exception()
                except FileNotFoundError:
                    raise TestSuiteError(stderr)
                
        return (
            cov,
            stdout,
            stderr,
        )