from cowboy_lib.repo.repository import RepoCommitContext
from cowboy_lib.repo import SourceRepo, GitRepo
from cowboy_lib.coverage import TestCoverage, Coverage
from cowboy_lib.test_modules.test_module import TestModule
from cowboy_lib.ast.code import NodeType
from cowboy_lib.repo.source_file import NodeNotFound, SameNodeException

from src.test_modules.models import TestModuleModel
from src.repo.models import RepoConfig

from pathlib import Path
from git import Repo
from logging import getLogger
from typing import List, Tuple


logger = getLogger("test_results")


class ExpVarDeleteFuncs(Exception):
    pass


# TODO: implement on TestCoverage
def find_file_cov_for_tm(tm: TestModule, base_cov: TestCoverage) -> Coverage:
    try:
        return next(
            filter(
                lambda x: x.filename == str(tm.targeted_files(base_path=False)[0]),
                base_cov.cov_list,
            )
        )
    except StopIteration:
        return None


def num_funcs_to_delete(tm: TestModule, to_keep: int = 0, to_delete: int = 0) -> int:
    """
    Returns the number of functions to delete or keep from a test module
    """
    print("to_keep: ", to_keep, "to_delete:", to_delete)
    if to_keep and to_delete:
        raise Exception("Cannot have both values > 0")

    # always leave at least one test
    if to_keep:
        num_to_del = max(0, len(tm.tests) - to_keep)
        return num_to_del
    elif to_delete:
        num_to_del = min(len(tm.tests) - 1, to_delete)
        return num_to_del
    else:
        raise ExpVarDeleteFuncs


# for every experiment, we potentially create two new branches
# br1: keep2
# br2: keep2/mod1 or keep2/expid
def nuke_name_br(to_keep, to_delete):
    branch = f"{'keep' + str(to_keep) if to_keep else 'del' + str(to_delete)}"
    return branch


def exp_name_br(exp_id: str):
    return exp_id


def create_nuked_branch(
    tms: List[TestModule],
    src_repo: SourceRepo,
    git_repo: GitRepo,
    branch_name: str,
    to_keep: int = 0,
    to_delete: int = 0,
):
    """
    Modifies all test files by adding or deleting a set number of tests, then commits
    the changes to
    """
    total_deleted = 0
    for tm in tms:
        # TODO: would need to change this loop to handle files
        logger.info(f"Generating augmented tests for {tm.name} in {tm.path}")

        to_exclude = []
        # BUG: tm.tests gets modified somehow
        num_to_del = num_funcs_to_delete(tm, to_keep=to_keep, to_delete=to_delete)
        total_tests = len(tm.tests)

        logger.info(f"Deleting {num_to_del}/{total_tests} tests from {tm.name}")

        for func in tm.tests[:num_to_del]:
            try:
                to_exclude.append((func, tm.test_file.path))
                # CARE: this operation has changes state of src_repo,
                # which is then propagated to strategy below
                src_repo.find_file(tm.path).delete(
                    func.name, node_type=NodeType.Function
                )
                # mirror the modifications made to src_repo
                # CARE: this only modifies TestFile, but not the nodes
                # TODO: figure out why the double delete here didnt work
                # tm.test_file.delete(func.name, node_type=NodeType.Function)

                src_repo.write_file(tm.path)
                total_deleted += 1
            except (NodeNotFound, SameNodeException) as e:
                print(e)
                continue

    git_repo.checkout(branch_name, new=True)
    git_repo.add_n_commit([str(tm.path) for tm in tms], f"Delete {total_deleted} tests")


def run_experiment(
    repo: RepoConfig,
    test_modules: List[TestModuleModel],
    to_keep: int = 0,
    to_delete: int = 0,
):
    src_repo = SourceRepo(Path(repo.source_folder))
    git_repo = GitRepo(Path(repo.source_folder))
    tms = [tm.serialize(src_repo) for tm in test_modules]

    base_cov = repo.base_cov()
    nuked_branch = nuke_name_br(to_keep, to_delete)

    if not git_repo.branch_exists(nuked_branch):
        print("Creating new branch")
        create_nuked_branch(tms, src_repo, git_repo, nuked_branch, to_keep, to_delete)

    git_repo.checkout(nuked_branch)

    print(f"Finished modifying repo: {src_repo.repo_path}")

    # for tm in test_modules:
    #     # we need to update fs so we can collect the coverage on the deleted tests
    #     # to compare it
    #     del_res, *_ = self.repo_ctxt.runner.run_test(exclude_tests=to_exclude)
    #     del_cov = base_cov.coverage - del_res.coverage
    #     logger.info(f"Deleted coverage: {del_cov.total_cov.covered}")

    #     if del_cov.total_cov.covered <= 0:
    #         logger.info(
    #             f"Skipping {tm.name}, no coverage difference: {del_cov.total_cov.misses}"
    #         )
    #         zero_improvement_tests += f"{tm.name}\n"
    #         continue

    #     # TODO: we need to use base_path from RepoPath here
    #     # we may have just deleted the targeted coverage from abvoe
    #     tgt_file = tm.targeted_files()[0]
    #     tgt_filecov_before = del_cov.get_file_cov(
    #         tgt_file, self.repo_ctxt.repo_path
    #     )
    #     tgt_filecov_before.read_line_contents(self.repo_ctxt.repo_path)
    #     logger.info(
    #         f"Target file coverage: {tgt_filecov_before} : {tgt_filecov_before.filename}"
    #     )

    #     total_coverage += del_cov.total_cov.covered

    #     evaluator_inst: Evaluator = evaluator(
    #         self.repo_ctxt.runner,
    #         self.repo_ctxt.git_repo,
    #         self.repo_ctxt.src_repo,
    #     )
    #     strat_instance: BaseTestStrategy = strategy(
    #         tm,
    #         self.repo_ctxt,
    #         evaluator_inst,
    #         del_res,
    #         tgt_filecov_before,
    #     )
    #     improved, failed, no_improve = await strat_instance.generate_test(
    #         n_times=1
    #     )

    #     print("Improved: ")
    #     for imp in improved:
    #         print(imp)

    #     self.save_results(tm, del_cov, improved, failed, no_improve)
    #     num_improve = len(improved)
    #     num_failed = len(failed)
    #     num_noimprove = len(no_improve)

    #     logger.info(
    #         f"Results for TM: {tm.name} => Improve: {num_improve}, Failed: {num_failed}, NoImprove: {num_noimprove}"
    #     )

    #     total_improvement += sum(
    #         [test[1].total_cov.covered for test in improved]
    #     )

    # except LintException as e:
    #     logger.info(f"Linting error: {e} on {tm.path}")
    #     continue

    # except SameNodeException as e:
    #     logger.info(f"SameNodeException on class: {tm.name}")
    #     continue

    # except Exception as e:
    #     logger.info(
    #         f"Exception on class: {tm.name} in {tm.path}",
    #         exc_info=True,
    #     )

    # logger.info(f"Final Results: {results}")
    # logger.info(f"Total improvement: {total_improvement}/{total_coverage}")
    # logger.info(f"Zero improvement tests: {zero_improvement_tests}")
    # logger.info(f"Run complete for {self.repo_ctxt.exp_id} ")
