from cowboy_lib.repo.source_repo import SourceRepo
from cowboy_lib.coverage import TestCoverage, CoverageResult
from cowboy_lib.test_modules.test_module import TestModule, TargetCode
from cowboy_lib.utils import testfiles_in_coverage

from src.queue.core import TaskQueue

from src.runner.service import run_test, RunServiceArgs

from logging import getLogger
from typing import List, Tuple


logger = getLogger(__name__)


class TestInCoverageException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msg = "Test files are included in coverage report"


async def get_tm_target_coverage(
    src_repo: SourceRepo,
    tm: TestModule,
    base_cov: CoverageResult,
    run_args: RunServiceArgs,
) -> Tuple[TestModule, List[TargetCode]]:
    """
    Test augmenting existing test classes by deleting random test methods, and then
    having LLM strategy generate them. Coverage is taken:
    1. After the deletion
    2. After the deletion with newly generated LLM testcases

    The diff measures how well we are able to supplant the coverage of the deleted methods
    """

    if testfiles_in_coverage(base_cov.coverage, src_repo):
        raise TestInCoverageException

    # First loop we find the total coverage of each test by itself
    only_module = [tm.name]
    # coverage with ONLY the current test module turned on
    print("Running initial test ... ", tm.name)

    module_cov = await run_test(
        run_args,
        include_tests=only_module,
    )

    module_diff = base_cov.coverage - module_cov.coverage
    total_cov_diff = module_diff.total_cov.covered
    if total_cov_diff > 0:
        # part 2:
        single_covs = []
        for test in tm.tests:
            print("Running test ... ", test.name)
            # tm.test_file.delete(test.name, node_type=test.type)
            # deleted_file = PatchFile(tm.test_file.path, tm.test_file.to_code())
            # with PatchFileContext(repo_ctxt.git_repo, deleted_file):

            # exclude_test = get_exclude_path(test, tm.test_file.path)
            single_cov = await run_test(
                run_args,
                exclude_tests=[(test, tm.test_file.path)],
                include_tests=only_module,
            )
            print("Test results: ", single_cov.coverage.total_cov.covered)

            print(
                f"Module cov: {module_cov.coverage.total_cov.covered}, Single cov: {single_cov.coverage.total_cov.covered}"
            )

            single_diff = (module_cov.coverage - single_cov.coverage).cov_list
            for c in single_diff:
                logger.info(
                    f"Changed coverage from deleting {test.name}:\n {c.__str__()}"
                )

            # dont think we actually need this here .. confirm
            tm.test_file = src_repo.get_file(tm.test_file.path)
            single_covs.extend(single_diff)

        # re-init the chunks according to the aggregated individual test coverages
        tm.set_chunks(
            single_covs,
            source_repo=src_repo,
            base_path=src_repo.repo_path,
        )

        print(f"Chunks: \n{tm.print_chunks()}")
    # Find out what's the reason for the missed tests
    else:
        logger.info(f"No coverage difference found for {tm.name}")

    return tm, tm.chunks
