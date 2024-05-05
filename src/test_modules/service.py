# from .models import TestModule
# Long term tasks represent tasks that we potentially want to offload to celery
from src.longterm_tasks import get_tm_target_coverage

from src.task_queue.core import TaskQueue
from src.repo.models import RepoConfig
from src.repo_ctxt import RepoTestContext
from src.auth.models import CowboyUser
from src.database.core import Session
from src.runner.service import run_test, RunServiceArgs
from src.ast.service import create_node, create_or_update_node

from src.ast.models import NodeModel

from .models import TestModuleModel, TestModule, TargetCode, TargetCodeModel
from .iter_tms import iter_test_modules

from typing import List


# TODO: get rid of this
def create_all_tms(
    *, db_session: Session, repo_conf: RepoConfig, repo_ctxt: RepoTestContext
):
    """Create all test modules for a repo."""
    test_modules = iter_test_modules(repo_ctxt.src_repo)

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


def create_target_code(
    db_session: Session,
    tm_model: TestModuleModel,
    chunk: TargetCode,
    func_scope: NodeModel = None,
    class_scope: NodeModel = None,
):
    """Create a target code chunk for a test module."""
    target_code = TargetCodeModel(
        test_module_id=tm_model.id,
        start=chunk.range[0],
        end=chunk.range[1],
        filepath=str(chunk.filepath),
        func_scope=func_scope,
        class_scope=class_scope,
    )

    db_session.add(target_code)
    db_session.commit()

    return target_code


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


# TODO: need to add a check here to not rerun baseline for nodes that
# have not been changed ... but need to be aware of repo changes and how this affects
# nodes
async def get_tgt_coverage(
    *,
    db_session: Session,
    task_queue: TaskQueue,
    curr_user: CowboyUser,
    repo_config: RepoConfig,
    tm_names: List[str]
):
    """Generates a target coverage for a test module."""

    repo_ctxt = RepoTestContext(repo_config)
    run_args = RunServiceArgs(curr_user.id, repo_config.repo_name, task_queue)

    base_cov = await run_test(run_args)
    tm_models = get_tms_by_names(
        db_session=db_session, repo_id=repo_config.id, tm_names=tm_names
    )
    total_tms = [tm_model.serialize(repo_ctxt.src_repo) for tm_model in tm_models]
    unbased_tms = [tm for tm in total_tms if not tm.chunks]
    print("Len unbased ")

    # zip tm_model because we need to update it later in the code
    for tm_model, tm in zip(tm_models, unbased_tms):
        # generate src to test mappings
        tm, targets = await get_tm_target_coverage(repo_ctxt, tm, base_cov, run_args)

        # store chunks and their nodes
        target_chunks = []
        for tgt in targets:
            func_scope = (
                create_or_update_node(
                    db_session=db_session,
                    node=tgt.func_scope,
                    repo_id=repo_config.id,
                    filepath=str(tgt.filepath),
                )
                if tgt.func_scope
                else None
            )
            class_scope = (
                create_or_update_node(
                    db_session=db_session,
                    node=tgt.class_scope,
                    repo_id=repo_config.id,
                    filepath=str(tgt.filepath),
                )
                if tgt.class_scope
                else None
            )

            target_chunks.append(
                create_target_code(
                    db_session=db_session,
                    tm_model=tm_model,
                    chunk=tgt,
                    func_scope=func_scope,
                    class_scope=class_scope,
                )
            )

            tm_model.target_chunks = target_chunks
            update_tm(db_session=db_session, tm_model=tm_model)
