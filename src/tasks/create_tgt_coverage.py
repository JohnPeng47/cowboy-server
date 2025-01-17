from src.lib.repo import SourceRepo
from src.lib.test_modules import TargetCode

# from .models import TestModule
# # Long term tasks represent tasks that we potentially want to offload to celery
from src.tasks.get_baseline_parallel import get_tm_target_coverage

from src.queue.core import TaskQueue
from src.repo.models import RepoConfig
from src.test_modules.models import TestModuleModel
from src.ast.models import NodeModel
from src.coverage.models import CoverageModel, coverage_to_model 
from src.runner.service import RunServiceArgs
from src.target_code.models import TargetCodeModel
from src.utils import async_timed
from src.logger import buildtm_logger as log

from sqlalchemy.orm import Session

from pathlib import Path
from typing import List, Callable


def tgtcode_to_model(
    tc: TargetCode,
    cov_model: CoverageModel,
    repo_id: int,
    tm_model: TestModuleModel,
) -> TargetCodeModel:
    """
    Create target code models with associated nodes in a single transaction
    """
    func_scope = (
        NodeModel(
            repo_id=repo_id,
            testfilepath=str(tc.filepath),
            name=tc.func_scope.name,
            node_type=tc.func_scope.node_type,
        )
        if tc.func_scope
        else None
    )
    class_scope = (
        NodeModel(
            repo_id=repo_id,
            testfilepath=str(tc.filepath), 
            name=tc.class_scope.name,
            node_type=tc.class_scope.node_type,
        )
        if tc.class_scope
        else None
    )

    return TargetCodeModel(
        start=tc.range[0],
        end=tc.range[1],
        lines=tc.lines,
        filepath=str(tc.filepath),
        func_scope=func_scope,
        class_scope=class_scope,
        test_module_id=tm_model.id,
        coverage_id=cov_model.id,
    )

@async_timed
async def create_tgt_coverage(
    *,
    db_session: Session,
    task_queue: TaskQueue,
    repo: RepoConfig,
    tm_models: List[TestModuleModel],
    run_test: Callable,
    overwrite: bool = True,
):
    """
    Important function that sets up relationships between TestModule, TargetCode and
    Coverage
    """
    repo_path = Path(repo.source_folder)
    src_repo = SourceRepo(repo_path)
    run_args = RunServiceArgs(repo.user_id, task_queue)
    base_cov = repo.base_cov

    # NEWDESIGN: in future, consider putting detecting TM updates due to mapped
    # module changes here

    # NEWTODO: Rewrunning base_cov is too expensive everytime but we do want some way 
    # of keeping the coverage information to be updated
    # if overwrite or not base_cov:
    #     log.info("Overwriting base coverage ... th ")
    #     cov_res = await run_test(repo.repo_name, run_args)
    #     base_cov = cov_res.coverage
    #     upsert_coverage(
    #         db_session=db_session, repo_id=repo.id, cov_list=base_cov.cov_list
    #     )

    for tm_model in tm_models:
        log.info(f"Building target coverage for: {tm_model.name}")
        # only overwrite existing target_chunks if overwrite flag is set
        if not overwrite and tm_model.target_chunks:
            log.info(f"Skipping {tm_model.name} cuz overwrite: {overwrite}, has_target_chunks: {(bool(tm_model.target_chunks))}")
            continue

        tm = tm_model.serialize(src_repo)

        # generate src th 
        tgt_chunks = await get_tm_target_coverage(
            repo.repo_name, src_repo, tm, base_cov, run_test, run_args
        )
        target_models = []
        for tc in tgt_chunks:
            file_cov = base_cov.get_file_cov(tc.filepath)
            # NEWDESIGN: we are okay with generating new coverage model here for now
            # UPDATE: actually there is issue with null ID here so coverage model is not being created properly
            file_cov_model = coverage_to_model(file_cov)
            target_models.append(tgtcode_to_model(tc, file_cov_model, repo.id, tm_model))

        # TODO: convert this to a Logfire log?
        # log.info(f"{tm_model.name} Chunks: ")
        # for t in target_models:
        #     log.info(t.to_str())

        tm_model.target_chunks = target_models
        db_session.merge(tm_model)
        db_session.commit()