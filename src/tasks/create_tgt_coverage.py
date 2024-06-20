from cowboy_lib.repo import SourceRepo
from cowboy_lib.test_modules import TargetCode

# from .models import TestModule
# # Long term tasks represent tasks that we potentially want to offload to celery
from src.tasks.get_baseline_parallel import get_tm_target_coverage

# from src.tasks.get_baseline import get_tm_target_coverage
from src.queue.core import TaskQueue
from src.repo.models import RepoConfig
from src.auth.models import CowboyUser
from src.test_modules.models import TestModuleModel

from src.runner.service import run_test, RunServiceArgs
from src.ast.service import create_node, create_or_update_node
from src.test_modules.service import get_tms_by_names, update_tm
from src.target_code.service import create_target_code
from src.coverage.service import get_cov_by_filename, create_or_update_cov
from src.utils import async_timed

from sqlalchemy.orm import Session

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


# TODO:
@async_timed
async def create_tgt_coverage(
    *,
    db_session: Session,
    task_queue: TaskQueue,
    repo: RepoConfig,
    tm_models: List[TestModuleModel],
    overwrite: bool = True
):
    """
    Important function that sets up relationships between TestModule, TargetCode and
    Coverage
    """
    src_repo = SourceRepo(Path(repo.source_folder))
    run_args = RunServiceArgs(repo.user_id, repo.repo_name, task_queue)
    base_cov = repo.base_cov

    for cov in base_cov.cov_list:
        create_or_update_cov(db_session=db_session, repo_id=repo.id, coverage=cov)

    for tm_model in tm_models:
        print("TM: ", tm_model.name)
        # only overwrite existing target_chunks if overwrite flag is set
        if not overwrite and tm_model.target_chunks:
            print("Skipping")
            continue

        tm = tm_model.serialize(src_repo)
        # generate src to test mappings
        tm, targets = await get_tm_target_coverage(src_repo, tm, base_cov, run_args)
        for t in targets:
            print("Target code: ", t.filepath)

        # store chunks and their nodes
        tgt_code_chunks = create_tgt_code_models(targets, db_session, repo.id, tm_model)

        tm_model.target_chunks = tgt_code_chunks
        update_tm(db_session=db_session, tm_model=tm_model)
