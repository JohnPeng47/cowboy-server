from src.eval.create_dataset import handicap_tm
from tests.utils import GitCommitContext
import pytest
from src.repo.models import RepoConfig
from cowboy_lib.repo import SourceRepo
from src.local.db import get_tm

pytestmark = pytest.mark.asyncio

async def test_handicap_tm(source_repo: SourceRepo):
    """Test that we only return coverage for removed tests that is apart of the targeted srcfiles"""

    TARGET_SRC = "c.py"

    with GitCommitContext(source_repo.repo_path,"0b5e9e90d83bb15d6e35fa9a42a101dbb8da7a5d"):       
        tm = get_tm("testrepo", "test_c.py")

        row, _, _ = await handicap_tm(
            dataset=None,
            targeted_srcfiles=[TARGET_SRC],
            repo_name="testrepo",
            tm=tm,
            repo_path=source_repo.repo_path,
            to_keep=1,
            ask_confirm=False
        )

        # check removed_tests coverage is in TARGET_SRC
        for test in row.removed_tests:
            for cov in test.cov.cov_list:
                assert cov.filename == TARGET_SRC
        
        # check expected coverage is in TARGET_SRC
        for coverage in row.expected.cov_list:
            assert coverage.filename == TARGET_SRC

        # should write a check for equality between these two

        assert row.expected.total_cov.stmts == 20
        assert row.expected.total_cov.misses == 7
        assert row.expected.total_cov.covered == 13