from cowboy_lib.repo import GitRepo, SourceRepo

from src.utils import gen_random_name
from src.auth.models import CowboyUser
from src.test_modules.service import create_all_tms
from src.config import REPOS_ROOT
from src.runner.service import run_test, RunServiceArgs
from src.queue.core import TaskQueue
from src.coverage.service import upsert_coverage

from .models import RepoConfig, RepoConfigCreate

from pathlib import Path
from logging import getLogger
from fastapi import HTTPException


logger = getLogger(__name__)


def get(*, db_session, curr_user: CowboyUser, repo_name: str) -> RepoConfig:
    """Returns a repo based on the given repo name."""
    return (
        db_session.query(RepoConfig)
        .filter(RepoConfig.repo_name == repo_name, RepoConfig.user_id == curr_user.id)
        .one_or_none()
    )


def get_or_raise(*, db_session, curr_user: CowboyUser, repo_name: str) -> RepoConfig:
    """Returns a repo based on the given repo name."""
    repo = (
        db_session.query(RepoConfig)
        .filter(
            RepoConfig.repo_name == repo_name,
            RepoConfig.user_id == curr_user.id,
        )
        .one_or_none()
    )
    # TODO: consider raising pydantic Validation error here instead
    # seems to be what dispatch does
    if not repo:
        raise HTTPException(status_code=400, detail=f"Repo {repo_name} not found")

    return repo


def get_all(*, db_session) -> list[RepoConfig]:
    """Returns all repos."""
    return db_session.query(RepoConfig).all()


def get_by_id_or_raise(
    *, db_session, curr_user: CowboyUser, repo_id: int
) -> RepoConfig:
    """Returns a repo based on the given repo id."""
    repo = (
        db_session.query(RepoConfig)
        .filter(RepoConfig.id == repo_id, RepoConfig.user_id == curr_user.id)
        .one_or_none()
    )
    if not repo:
        raise HTTPException(status_code=400, detail=f"Repo {repo_id} not found")

    return repo


def get_experiment(*, db_session, curr_user: CowboyUser, repo_name: str) -> RepoConfig:
    """Returns a repo based on the given repo name."""

    return (
        db_session.query(RepoConfig)
        .filter(
            RepoConfig.repo_name == repo_name,
            RepoConfig.user_id == curr_user.id,
            RepoConfig.is_experiment == True,
        )
        .one_or_none()
    )


def delete(*, db_session, curr_user: CowboyUser, repo_name: str) -> RepoConfig:
    """Deletes a repo based on the given repo name."""

    repo = get(db_session=db_session, curr_user=curr_user, repo_name=repo_name)
    if repo:
        db_session.delete(repo)
        db_session.commit()

        GitRepo.delete_repo(Path(repo.source_folder))
        return repo

    return None


def clean(*, db_session, curr_user: CowboyUser, repo_name: str) -> RepoConfig:
    """Cleans repo branches."""

    repo = get(db_session=db_session, curr_user=curr_user, repo_name=repo_name)
    if repo:
        GitRepo.clean_branches(Path(repo.source_folder))
        return repo

    return None


async def create(
    *,
    db_session,
    curr_user: CowboyUser,
    repo_in: RepoConfigCreate,
    task_queue: TaskQueue,
) -> RepoConfig:
    """Creates a new repo."""

    repo_dst = None
    try:
        repo = RepoConfig(
            **repo_in.dict(),
            user_id=curr_user.id,
        )

        repo_dst = Path(REPOS_ROOT) / repo.repo_name / gen_random_name()
        GitRepo.clone_repo(repo_dst, repo.url)

        src_repo = SourceRepo(repo_dst)
        repo.source_folder = str(repo_dst)
        db_session.add(repo)
        # have to commit here or because run_test depends on existing RepoConfig
        db_session.commit()

        # create test modules
        # create_all_tms(db_session=db_session, repo_conf=repo, src_repo=src_repo)

        # get base coverage for repo
        service_args = RunServiceArgs(user_id=curr_user.id, task_queue=task_queue)
        cov_res = await run_test(repo.repo_name, service_args)
        upsert_coverage(
            db_session=db_session, repo_id=repo.id, cov_list=cov_res.coverage.cov_list
        )

        db_session.commit()
        return repo

    except Exception as e:
        db_session.rollback()
        if repo:
            delete(db_session=db_session, curr_user=curr_user, repo_name=repo.repo_name)

        if repo_dst:
            GitRepo.delete_repo(repo_dst)

        logger.error(f"Failed to create repo configuration: {e}")
        raise


def update(
    *, db_session, curr_user: CowboyUser, repo_name: int, repo_in: RepoConfigCreate
) -> RepoConfig:
    """Updates a repo."""

    repo = get(db_session=db_session, curr_user=curr_user, repo_name=repo_name)
    if not repo:
        return None

    repo.update(repo_in)
    db_session.commit()

    return repo


async def create_or_update(
    *,
    db_session,
    curr_user: CowboyUser,
    repo_in: RepoConfigCreate,
    task_queue: TaskQueue,
) -> RepoConfig:
    """Create or update a repo"""
    repo_conf = get(
        db_session=db_session, curr_user=curr_user, repo_name=repo_in.repo_name
    )

    if not repo_conf:
        return await create(
            db_session=db_session,
            curr_user=curr_user,
            repo_in=repo_in,
            task_queue=task_queue,
        )

    return update(
        db_session=db_session,
        curr_user=curr_user,
        repo_name=repo_in.repo_name,
        repo_in=repo_in,
    )


def list(*, db_session, curr_user: CowboyUser) -> RepoConfig:
    """Lists all repos for a user."""

    return db_session.query(RepoConfig).filter(RepoConfig.user_id == curr_user.id).all()
