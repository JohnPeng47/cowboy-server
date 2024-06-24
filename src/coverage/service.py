from cowboy_lib.coverage import Coverage
from src.test_gen.models import AugmentTestResult

from .models import CoverageModel

from sqlalchemy.orm import Session
from typing import List


def upsert_coverage(
    *,
    db_session: Session,
    repo_id: int,
    cov_list: List[Coverage],
    test_result_id: int = None
):
    """Deletes old coverage and insert new"""

    db_session.query(CoverageModel).filter(CoverageModel.repo_id == repo_id).delete()

    for coverage in cov_list:
        # if it does not exist, create
        cov_model = CoverageModel(
            filename=coverage.filename,
            covered_lines=",".join(map(str, coverage.covered_lines)),
            missing_lines=",".join(map(str, coverage.missing_lines)),
            stmts=coverage.stmts,
            misses=coverage.misses,
            covered=coverage.covered,
            repo_id=repo_id,
            test_result_id=test_result_id,
        )
        db_session.add(cov_model)

    db_session.commit()
    return cov_model


def get_cov_by_filename(
    *, db_session: Session, repo_id: int, filename: str
) -> CoverageModel:
    """Get a coverage model by filename."""

    return (
        db_session.query(CoverageModel)
        .filter(CoverageModel.filename == filename, CoverageModel.repo_id == repo_id)
        .one_or_none()
    )


def get_cov_by_id(*, db_session: Session, repo_id: int, id: int) -> CoverageModel:
    """Get a coverage model by id."""

    return (
        db_session.query(CoverageModel)
        .filter(CoverageModel.id == id, CoverageModel.repo_id == repo_id)
        .one_or_none()
    )
