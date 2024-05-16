from cowboy_lib.repo import SourceRepo
from cowboy_lib.test_modules import TargetCode

# from .models import TestModule
# # Long term tasks represent tasks that we potentially want to offload to celery
from src.tasks.get_baseline_parallel import get_tm_target_coverage
from src.queue.core import TaskQueue
from src.repo.models import RepoConfig
from src.auth.models import CowboyUser
from src.database.core import Session
from src.test_modules.models import TestModuleModel

from src.runner.service import run_test, RunServiceArgs
from src.ast.service import create_node, create_or_update_node
from src.test_modules.service import get_tms_by_names, update_tm
from src.target_code.service import create_target_code
from src.coverage.service import get_cov_by_filename, create_or_update_cov

from pathlib import Path
from typing import List


def create_tgt_code_models(
    tgt_code_chunks: List[TargetCode],
    db_session: Session,
    repo_id: int,
    tm_model: TestModuleModel,
) -> List[TargetCode]:
    """
    Create target code models
    """
    target_chunks = []
    for tgt in tgt_code_chunks:
        func_scope = (
            create_or_update_node(
                db_session=db_session,
                node=tgt.func_scope,
                repo_id=repo_id,
                filepath=str(tgt.filepath),
            )
            if tgt.func_scope
            else None
        )
        class_scope = (
            create_or_update_node(
                db_session=db_session,
                node=tgt.class_scope,
                repo_id=repo_id,
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
                cov_model=get_cov_by_filename(
                    db_session=db_session,
                    repo_id=repo_id,
                    filename=str(tgt.filepath),
                ),
                func_scope=func_scope,
                class_scope=class_scope,
            )
        )

    return target_chunks


# TODO: need to add a check here to not rerun baseline for nodes that
# have not been changed ... but need to be aware of repo changes and how this affects
# nodes
# should probably rename this, way too inncuous for important function
async def get_tgt_coverage(
    *,
    db_session: Session,
    task_queue: TaskQueue,
    curr_user: CowboyUser,
    repo_config: RepoConfig,
    tm_names: List[str]
):
    """
    Important function that sets up relationships between TestModule, TargetCode and
    Coverage
    """
    src_repo = SourceRepo(Path(repo_config.source_folder))
    run_args = RunServiceArgs(curr_user.id, repo_config.repo_name, task_queue)

    # replace this with TestCoverage
    base_cov = await run_test(run_args)
    for cov in base_cov.coverage.cov_list:
        create_or_update_cov(
            db_session=db_session, repo_id=repo_config.id, coverage=cov
        )

    tm_models = get_tms_by_names(
        db_session=db_session, repo_id=repo_config.id, tm_names=tm_names
    )
    total_tms = [tm_model.serialize(src_repo) for tm_model in tm_models]
    unbased_tms = [tm for tm in total_tms if not tm.chunks]

    # zip tm_model because we need to update it later in the code
    for tm_model, tm in zip(tm_models, unbased_tms):
        # generate src to test mappings
        tm, targets = await get_tm_target_coverage(src_repo, tm, base_cov, run_args)

        # store chunks and their nodes
        target_code_models = create_tgt_code_models(
            targets, db_session, repo_config.id, tm_model
        )

        tm_model.target_chunks = target_code_models
        update_tm(db_session=db_session, tm_model=tm_model)
