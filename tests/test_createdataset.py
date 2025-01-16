from src.eval.create_dataset import handicap_tm
from tests.utils import GitCommitContext
import pytest
from src.repo.models import RepoConfig
from cowboy_lib.repo import SourceRepo
from src.local.db import get_tm

pytestmark = pytest.mark.asyncio

async def test_handicap_tm(source_repo: SourceRepo):
    with GitCommitContext(source_repo.repo_path,"bd4994316c320d031b6b08623d38affd0320ccc7"):        
        tm = get_tm("testrepo", "test_c.py")

        row, content, total_deleted = await handicap_tm(
            dataset=None,
            targeted_srcfiles=["src/a.py"],
            repo_name="testrepo",
            tm=tm,
            repo_path=source_repo.repo_path,
            to_keep=1,
            ask_confirm=False
        )

        print(row.removed_tests)

        for test in row.removed_tests:
            for cov in test.cov.cov_list:
                print("COVERAGE: ", cov)
                assert cov.filename == "test_c.py"