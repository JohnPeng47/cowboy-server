from src.runner.local.run_test import run_test
from src.test_modules.iter_tms import iter_test_modules

from src.lib.repo import SourceRepo

from pathlib import Path
import asyncio


async def main():
    repo_name = "codecovapi-neutered"
    src_repo = SourceRepo(Path("/home/ubuntu/codecov-api"))
    only_module = iter_test_modules(src_repo, lambda tm: tm.name == "FlagCommandsTest")[0]

    module_cov = await run_test(
        repo_name,
        None,
        # part1: collect the coverage of a single module only
        include_tests=only_module,
        # stream = True,
        use_cache=False,
        delete_last=False
    )

    for cov in module_cov.get_coverage().cov_list:
        if cov.covered > 0:
            print(f"File: {cov.filename}, Coverage: {(cov.covered / cov.stmts * 100):.2f}%")

if __name__ == "__main__":
    asyncio.run(main())