from cowboy_lib.repo.source_repo import SourceRepo

from .composer import Composer

from src.database.core import Session
from src.auth.models import CowboyUser

from src.repo.service import get as get_repo
from src.test_modules.service import get_tm_by_name
from src.runner.service import RunServiceArgs
from src.task_queue.core import TaskQueue

from src.test_gen.augment_test.strats import AUGMENT_STRATS
from src.longterm_tasks.evaluators import AUGMENT_EVALS

from pathlib import Path


async def augment_test(
    *,
    task_queue: TaskQueue,
    db_session: Session,
    curr_user: CowboyUser,
    tm_name: str,
    repo_name: str
):
    """
    Generate test cases for the given test module using the specified strategy and evaluator
    """
    repo = get_repo(db_session=db_session, curr_user=curr_user, repo_name=repo_name)
    test_module = get_tm_by_name(
        db_session=db_session, repo_id=repo.id, tm_name=tm_name
    )

    run_args = RunServiceArgs(
        user_id=curr_user.id, repo_name=repo_name, task_queue=task_queue
    )

    src_repo = SourceRepo(Path(repo.source_folder))

    composer = Composer(
        strat="WITH_CTXT",
        evaluator="ADDITIVE",
        run_args=run_args,
        src_repo=src_repo,
        test_input=test_module.serialize(src_repo),
    )

    return await composer.generate_test(n_times=1)
