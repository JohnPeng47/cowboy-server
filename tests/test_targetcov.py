from src.tasks.get_baseline_parallel import get_tm_target_coverage
from src.local.db import get_tm
from src.runner.local.run_test import run_test
from src.test_modules.iter_tms import iter_test_modules

from src.lib.repo import SourceRepo

import pytest
from tests.utils import GitCommitContext

@pytest.mark.asyncio 
async def test_get_tm_target_coverage(source_repo: SourceRepo):
    with GitCommitContext(source_repo.repo_path, "0b5e9e90d83bb15d6e35fa9a42a101dbb8da7a5d"):
        tm = iter_test_modules(source_repo, lambda tm: tm.name == "test_c.py")[0]
        
        # Get base coverage like in test_runtest.py
        base_cov = await run_test(
            "testrepo",
            None,
            use_cache=False
        )

        # Execute get_tm_target_coverage
        chunks = await get_tm_target_coverage(
            repo_name="testrepo",
            src_repo=source_repo,
            tm=tm,
            base_cov=base_cov.get_coverage(),
            run_test=run_test,
            run_args=None
        )

        # maybe a more comprehensive test?        
        assert len(chunks) == 14