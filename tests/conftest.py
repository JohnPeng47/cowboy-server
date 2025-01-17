import pytest
from src.lib.repo import SourceRepo
from src.local.db import get_repo

from pathlib import Path


pytest_plugins = ['pytest_asyncio']

@pytest.fixture
def test_repoconfig():
    return get_repo("testrepo", ret_json=False)

@pytest.fixture
def source_repo(test_repoconfig):
    yield SourceRepo(Path(test_repoconfig.source_folder))