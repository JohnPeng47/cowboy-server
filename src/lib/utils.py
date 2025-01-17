from pathlib import Path
import subprocess
import os
import uuid
import random
import string
import shutil


def get_current_git_commit(repo_path: Path) -> str:
    """
    Uses subprocess to get the current git commit hash.

    Returns:
        str: The current git commit hash.
    """
    try:
        commit_hash = (
            subprocess.check_output(
                ["cd", str(repo_path.resolve()), "&&", "git", "rev-parse", "HEAD"],
                shell=True,
            )
            .strip()
            .decode("utf-8")
        )
        return commit_hash
    except subprocess.CalledProcessError as e:
        print(f"Error getting current git commit: {e}")
        return ""


def locate_python_interpreter():
    possible_interpreters = ["python", "python3"]

    for interpreter in possible_interpreters:
        # Check if the interpreter is in PATH
        path = shutil.which(interpreter)
        if path:
            return path

    # Try manually common locations
    common_locations = [
        "/usr/bin/python",
        "/usr/local/bin/python",
        "/usr/bin/python3",
        "/usr/local/bin/python3",
        "/bin/python",
        "/bin/python3",
        "/usr/sbin/python",
        "/usr/sbin/python3",
    ]

    for location in common_locations:
        if os.path.isfile(location) and os.access(location, os.X_OK):
            return location

    # As a last resort, try running "python --version" and "python3 --version"
    for interpreter in possible_interpreters:
        try:
            result = subprocess.run(
                [interpreter, "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return interpreter
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    raise FileNotFoundError("Python interpreter not found on this host")


def testfiles_in_coverage(base_cov, src_repo) -> bool:
    """
    Check if the test files are accidentally included in the coverage
    """
    for test_file in src_repo.test_files:
        for cov in base_cov.cov_list:
            if cov.filename.split(os.sep)[-1] == test_file.path.name:
                return True
    return False


def generate_id():
    """
    Generates a random UUID
    """
    return str(uuid.uuid4())


def gen_random_name():
    """
    Generates a random name using ASCII, 8 characters in length
    """

    return "".join(random.choices(string.ascii_lowercase, k=8))


def find_substring(string: str, substring: str):
    indices = []
    start = 0
    while start < len(string):
        start = string.find(substring, start)
        if start == -1:  # No more occurrences
            return indices
        indices.append(start)
        start += 1  # Move past the last found index to find subsequent matches

    return indices
