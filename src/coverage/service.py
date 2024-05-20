from cowboy_lib.coverage import Coverage
from src.test_gen.models import AugmentTestResult

from .models import CoverageModel

from sqlalchemy.orm import Session


def create_or_update_cov(
    *, db_session: Session, repo_id: int, coverage: Coverage, test_result_id: int = None
):
    """Create or update a coverage model from a coverage object."""
    cov_model = get_cov_by_filename(
        db_session=db_session, repo_id=repo_id, filename=coverage.filename
    )

    if cov_model:
        # if it exists update
        cov_model.covered_lines = ",".join(map(str, coverage.covered_lines))
        cov_model.missing_lines = ",".join(map(str, coverage.missing_lines))
        cov_model.stmts = coverage.stmts
        cov_model.misses = coverage.misses
        cov_model.covered = coverage.covered
        cov_model.test_result_id = test_result_id
    else:
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
