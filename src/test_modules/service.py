from cowboy_lib.repo import SourceRepo

# from .models import TestModule
# # Long term tasks represent tasks that we potentially want to offload to celery
from src.tasks.get_baseline_parallel import get_tm_target_coverage
from src.queue.core import TaskQueue
from src.repo.models import RepoConfig
from src.auth.models import CowboyUser
from src.database.core import Session

from src.runner.service import run_test, RunServiceArgs
from src.ast.service import create_node, create_or_update_node
from src.target_code.service import create_target_code
from src.coverage.service import get_cov_by_filename, create_or_update_cov
from src.coverage.models import CoverageModel

from .models import TestModuleModel, TestModule
from .iter_tms import iter_test_modules

from pathlib import Path
from typing import List


# def get_coverage_stats(tm: TestModule, cov_list: List[CoverageModel]):
#     """
#     Calculate coverage stats for
#     """
#     for cov in cov_list:
#         # this is
#         total_covered = cov.covered
#         tgt_covered = 0
#         missing = cov.misses

#         for chunk in tm.chunks:
#             if Path(chunk.filepath) == cov.filename:
#                 tgt_covered += len(chunk.lines)

#         score = tgt_covered + missing / total_covered if total_covered else 0
#         if score > 1:
#             # yeah ...
#             wtf += 1

#         recommended.append(
#             {
#                 "filename": cov.filename,
#                 "covered_pytest": covered,
#                 "missing": missing,
#                 "covered_baseline": actual,
#                 # this actually gives us a perfectly normalized score, since
#                 # actual < covered
#                 "score": score,
#                 "nodes": nodes,
#             }
#         )


# TODO: get rid of this
def create_all_tms(*, db_session: Session, repo_conf: RepoConfig, src_repo: SourceRepo):
    """Create all test modules for a repo."""
    test_modules = iter_test_modules(src_repo)

    for tm in test_modules:
        create_tm(db_session=db_session, repo_id=repo_conf.id, tm=tm)


def create_tm(*, db_session: Session, repo_id: str, tm: TestModule):
    """Create a test module and the nodes"""

    tm_model = TestModuleModel(
        name=tm.name,
        testfilepath=str(tm.test_file.path),
        commit_sha=tm.commit_sha,
        repo_id=repo_id,
    )

    # need to commit before so node has access to tm_model.id
    db_session.add(tm_model)
    db_session.commit()

    for node in tm.nodes:
        create_node(
            db_session=db_session,
            node=node,
            repo_id=repo_id,
            filepath=tm_model.testfilepath,
            test_module_id=tm_model.id,
        )

    return tm_model


def get_all_tms(*, db_session: Session, repo_id: str) -> List[TestModuleModel]:
    """
    Query all TMs for a repo
    """
    return (
        db_session.query(TestModuleModel)
        .filter(TestModuleModel.repo_id == repo_id)
        .all()
    )


def get_tms_by_names(
    *, db_session: Session, repo_id: str, tm_names: List[str]
) -> List[TestModuleModel]:
    """
    Query by name and return all if no names are provided
    """

    query = db_session.query(TestModuleModel).filter(TestModuleModel.repo_id == repo_id)
    if tm_names:
        query = query.filter(TestModuleModel.name.in_(tm_names))

    return query.all()


def get_tm_by_name(
    *, db_session: Session, repo_id: str, tm_name: str
) -> TestModuleModel:
    """
    Query by name and return all if no names are provided
    """

    query = db_session.query(TestModuleModel).filter(TestModuleModel.repo_id == repo_id)
    if tm_name:
        query = query.filter(TestModuleModel.name == tm_name)

    return query.one_or_none()


def update_tm(*, db_session: Session, tm_model: TestModuleModel):
    """
    Updates an existing TM
    """
    db_session.merge(tm_model)
    db_session.commit()

    return tm_model
