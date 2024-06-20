from cowboy_lib.repo import SourceRepo
from src.coverage.service import create_or_update_cov
from src.test_modules.service import (
    get_all_tms_sorted,
    get_tms_by_filename,
    get_tms_by_names,
)
from src.config import AUTO_GEN_SIZE

from .models import AugmentTestResult, TMSelectModeBase, TMSelectMode

from starlette.requests import Request
from typing import List


def save_all(*, db_session, test_results: List[AugmentTestResult]):
    for tr in test_results:
        db_session.add(tr)
    db_session.commit()


def create_test_result(
    *,
    db_session,
    repo_id,
    name,
    test_case,
    cov_list,
    tm_id,
    commit_hash,
    testfile,
    session_id,
    classname=None,
):
    tr_model = AugmentTestResult(
        name=name,
        test_case=test_case,
        test_module_id=tm_id,
        commit_hash=commit_hash,
        testfile=testfile,
        classname=classname,
        session_id=session_id,
        repo_id=repo_id,
    )

    create_or_update_cov(
        db_session=db_session,
        repo_id=repo_id,
        cov_list=cov_list,
        test_result_id=tr_model.id,
    )

    db_session.add(tr_model)
    db_session.commit()

    return tr_model


def get_test_result_by_id_or_raise(*, db_session, test_id) -> AugmentTestResult:
    return (
        db_session.query(AugmentTestResult)
        .filter(AugmentTestResult.id == test_id)
        .one_or_none()
    )


def get_test_results_by_sessionid(*, db_session, session_id) -> AugmentTestResult:
    return (
        db_session.query(AugmentTestResult)
        # only return undecided sessions
        .filter(
            AugmentTestResult.session_id == session_id, AugmentTestResult.decide == -1
        ).all()
    )


def update_test_result_decision(*, db_session, test_id, decision: int):
    test_result = get_test_result_by_id_or_raise(db_session=db_session, test_id=test_id)
    test_result.decide = decision
    db_session.commit()


def delete_test_results_by_sessionid(*, db_session, session_id):
    db_session.query(AugmentTestResult).filter(
        AugmentTestResult.session_id == session_id
    ).delete()

    db_session.commit()


def get_session_id(request: Request):
    return request.state.session_id


def select_tms(*, db_session, repo_id, request: TMSelectModeBase, src_repo: SourceRepo):
    if request.mode == TMSelectMode.AUTO.value:
        tm_models = get_all_tms_sorted(
            db_session=db_session, src_repo=src_repo, repo_id=repo_id, n=AUTO_GEN_SIZE
        )
    elif request.mode == TMSelectMode.FILE.value:
        tm_models = get_tms_by_filename(
            db_session=db_session, repo_id=repo_id, src_file=request.files
        )
    elif request.mode == TMSelectMode.TM.value:
        tm_models = get_tms_by_names(
            db_session=db_session, repo_id=repo_id, tm_names=request.tms
        )
    elif request.mode == TMSelectMode.ALL.value:
        tm_models = get_tms_by_names(
            db_session=db_session, repo_id=repo_id, tm_names=[]
        )

    return tm_models
