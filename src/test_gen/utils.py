from typing import List
from pathlib import Path
import subprocess


def gen_enumerated_code_str(code: List[str]) -> str:
    """
    Adds line numbers infront of source code like so:

    1: def test_something():
    2:     assert True

    """

    code.append("\n")
    # strip out newlines from code, idk how they got there
    code = [line.rstrip() for line in code]
    return "\n".join([f"{i}: {line}" for i, line in enumerate(code, start=1)])


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
