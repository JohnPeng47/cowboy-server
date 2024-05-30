from src.repo.models import RepoConfig
from .models import RepoStats

from contextlib import contextmanager
from sqlalchemy.orm import Session


@contextmanager
def update_repo_stats(*, db_session: Session, repo: RepoConfig):
    try:
        stats = db_session.query(RepoStats).filter_by(repo_id=repo.id).one_or_none()
        if not stats:
            stats = RepoStats(
                repo_id=repo.id, total_tests=0, accepted_tests=0, rejected_tests=0
            )
            db_session.add(stats)
        yield stats

        db_session.commit()
    except Exception as e:
        db_session.rollback()
        raise e
