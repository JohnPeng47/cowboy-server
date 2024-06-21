from cowboy_lib.repo.source_repo import SourceRepo
from cowboy_lib.coverage import TestCoverage, CoverageResult
from cowboy_lib.test_modules.test_module import TestModule, TargetCode
from cowboy_lib.utils import testfiles_in_coverage

from src.queue.core import TaskQueue

from src.runner.service import run_test, RunServiceArgs

from logging import getLogger
from typing import List, Tuple

import asyncio


logger = getLogger(__name__)


class TestInCoverageException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msg = "Test files are included in coverage report"


async def build_tm_src_mapping(
    src_repo: SourceRepo,
    tm: TestModule,
    base_cov: CoverageResult,
    run_args: RunServiceArgs,
) -> Tuple[TestModule, List[TargetCode]]:
    """
    Builds the mapping from each test inside a test module to
    a chunk of a source code file. The algorithm works by diffing the new coverage
    of each individual test with the coverage of the test module as a whole. The diff
    in lines covered are the lines that the test is responsible for covering
    """

    if testfiles_in_coverage(base_cov.coverage, src_repo):
        raise TestInCoverageException

    # First loop we find the total coverage of each test by itself
    only_module = [tm.name]
    # coverage with ONLY the current test module turned on
    print("Running initial test ... ", tm.name)

    # LAUREN 4: First we collect the coverage metric for the entire test module
    # via the run_test method, which puts a run_test task on a queue that is
    # regularly poll'd by the client (remember all unit test execution has to be
    # done in the client environment where their environment is installed)
    module_cov = await run_test(
        run_args,
        include_tests=only_module,
    )

    # LAUREN 8: Once run_test is finished, proceed to calculating the diff
    # between the coverage. Note that CoverageA - CoverageB is a __sub__ method
    # that just takes the set difference of Set(A) - Set(B), which is all of
    # the covered line in A but not B is
    module_diff = base_cov.coverage - module_cov.coverage
    total_cov_diff = module_diff.total_cov.covered
    if total_cov_diff > 0:
        chg_cov = []
        coroutines = []

        for test in tm.tests:
            print("Running test ... ", test.name)
            # get coverage for test with the current test turned off
            task = run_test(
                run_args,
                exclude_tests=[(test, tm.test_file.path)],
                include_tests=only_module,
            )
            coroutines.append(task)

        # do this to run tasks in paralell on the client
        cov_res = await asyncio.gather(*[t for t in coroutines])
        for test, cov_miss in zip(tm.tests, cov_res):
            print("Test results: ", cov_miss.coverage.total_cov.covered)
            print(
                f"Module cov: {module_cov.coverage.total_cov.covered}, Single cov: {cov_miss.coverage.total_cov.covered}"
            )

            # get the coverage diff between the total test module coverage and the coverage
            # when a test is excluded
            single_diff = (module_cov.coverage - cov_miss.coverage).cov_list
            for c in single_diff:
                logger.info(
                    f"Changed coverage from deleting {test.name}:\n {c.__str__()}"
                )

            # dont think we actually need this here .. confirm
            chg_cov.extend(single_diff)

        # re-init the chunks according to the aggregated individual test coverages
        tm.set_chunks(
            chg_cov,
            source_repo=src_repo,
            base_path=src_repo.repo_path,
        )

        print(f"Chunks: \n{tm.print_chunks()}")
    # Find out what's the reason for the missed tests
    else:
        logger.info(f"No coverage difference found for {tm.name}")

    return tm, tm.chunks
