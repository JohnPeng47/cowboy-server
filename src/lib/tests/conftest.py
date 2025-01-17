from src.lib.repo import GitRepo, SourceRepo
from pathlib import Path
import pytest

TEST_REPO = "tests/data/repos/codecov-cli-neuteured"


@pytest.fixture
def git_repo():
    return GitRepo(Path(TEST_REPO))


@pytest.fixture
def src_repo():
    return SourceRepo(Path(TEST_REPO))
