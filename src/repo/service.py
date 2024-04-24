from typing import Dict

from .models import RepoConfig

from src.auth.models import CowboyUser

from starlette.status import HTTP_409_CONFLICT


def get(*, db_session, curr_user: CowboyUser, repo_name: int) -> RepoConfig:
    """Returns a repo based on the given repo name."""

    return (
        db_session.query(RepoConfig)
        .filter(
            RepoConfig.repo_name == repo_name and RepoConfig.user_id == curr_user.id
        )
        .one_or_none()
    )


def delete(*, db_session, curr_user: CowboyUser, repo_name: int) -> RepoConfig:
    """Deletes a repo based on the given repo name."""

    repo = (
        db_session.query(RepoConfig)
        .filter(
            RepoConfig.repo_name == repo_name and RepoConfig.user_id == curr_user.id
        )
        .first()
    )

    if repo:
        db_session.delete(repo)
        db_session.commit()
        return repo

    return None


def create(*, db_session, curr_user: CowboyUser, repo_in: Dict) -> RepoConfig:
    """Creates a new repo."""

    repo = RepoConfig(
        **repo_in.dict(),
        user_id=curr_user.id,
    )

    db_session.add(repo)
    db_session.commit()

    return repo
