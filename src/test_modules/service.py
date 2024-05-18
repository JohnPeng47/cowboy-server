from cowboy_lib.repo import SourceRepo

from src.repo.models import RepoConfig
from src.database.core import Session
from src.ast.service import create_node

from .models import TestModuleModel, TestModule
from .iter_tms import iter_test_modules

from typing import List


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


def get_all_tms(*, db_session: Session, repo_id: str) -> List[TestModuleModel]:
    """
    Query all TMs for a repo
    """
    return (
        db_session.query(TestModuleModel)
        .filter(TestModuleModel.repo_id == repo_id)
        .all()
    )


def get_tms_by_filename(
    *, db_session: Session, repo_id: str, src_file: str
) -> List[TestModuleModel]:
    """
    Query all TMs for a repo
    """
    all_tms = get_all_tms(db_session=db_session, repo_id=repo_id)
    return [tm for tm in all_tms if src_file in tm.get_covered_files()]


def get_all_tms_sorted(
    *, db_session: Session, repo_id: str, src_repo: SourceRepo, n: int = 2
) -> List[TestModuleModel]:
    """
    Query all TMs for a repo
    """
    all_tms = get_all_tms(db_session=db_session, repo_id=repo_id)
    sorted_tms = sorted(all_tms, key=lambda tm: tm.agg_score(src_repo), reverse=True)
    select_tms = sorted_tms[:n]

    # update auto_gen flag on TMs
    for tm in select_tms:
        tm.auto_gen = True
        update_tm(db_session=db_session, tm_model=tm)

    return select_tms


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
