from src.auth.models import CowboyUser

from .models import RepoConfig, RepoConfigCreate

from src.repo_ctxt import RepoTestContext, create_repo, delete_repo
from src.test_modules.service import create_all_tms

from logging import getLogger

logger = getLogger(__name__)


def get(*, db_session, curr_user: CowboyUser, repo_name: str) -> RepoConfig:
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
        .one_or_none()
    )

    if repo:
        db_session.delete(repo)
        db_session.commit()

        delete_repo(repo_name)
        return repo

    return None


def create(
    *, db_session, curr_user: CowboyUser, repo_in: RepoConfigCreate
) -> RepoConfig:
    """Creates a new repo."""

    repo_conf = RepoConfig(
        **repo_in.dict(),
        user_id=curr_user.id,
    )

    forked_url, source_folder = create_repo(repo_conf)

    repo_conf.forked_url = forked_url
    repo_conf.source_folder = source_folder

    db_session.add(repo_conf)
    db_session.commit()

    # create test modules
    repo_ctxt = RepoTestContext(repo_conf)
    logger.info(f"Creating tms with source repo: ", repo_ctxt.src_repo)
    create_all_tms(db_session=db_session, repo_conf=repo_conf, repo_ctxt=repo_ctxt)

    return repo_conf


def update(
    *, db_session, curr_user: CowboyUser, repo_name: int, repo_in: RepoConfigCreate
) -> RepoConfig:
    """Updates a repo."""

    repo = (
        db_session.query(RepoConfig)
        .filter(
            RepoConfig.repo_name == repo_name and RepoConfig.user_id == curr_user.id
        )
        .one_or_none()
    )

    if not repo:
        return None

    repo.update(repo_in)
    db_session.commit()

    return repo


def create_or_update(
    *, db_session, curr_user: CowboyUser, repo_in: RepoConfigCreate
) -> RepoConfig:
    """Create or update a repo"""

    repo_conf = get(
        db_session=db_session, curr_user=curr_user, repo_name=repo_in.repo_name
    )

    if not repo_conf:
        return create(db_session=db_session, curr_user=curr_user, repo_in=repo_in)

    return update(
        db_session=db_session,
        curr_user=curr_user,
        repo_name=repo_in.repo_name,
        repo_in=repo_in,
    )


def list(*, db_session, curr_user: CowboyUser) -> RepoConfig:
    """Lists all repos for a user."""

    return db_session.query(RepoConfig).filter(RepoConfig.user_id == curr_user.id).all()
