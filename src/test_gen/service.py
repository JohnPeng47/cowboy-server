from .models import AugmentTestResult, UserDecision

from src.coverage.service import create_or_update_cov

from typing import List
from src.utils import generate_id


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
    classname=None
):
    tr_model = AugmentTestResult(
        name=name,
        test_case=test_case,
        test_module_id=tm_id,
        commit_hash=commit_hash,
        testfile=testfile,
        classname=classname,
        repo_id=repo_id,
    )

    for cov in cov_list:
        create_or_update_cov(
            db_session=db_session,
            repo_id=repo_id,
            coverage=cov,
            test_result_id=tr_model.id,
        )

    db_session.add(tr_model)
    db_session.commit()

    return tr_model


def get_test_results(*, db_session, session_id):
    return (
        db_session.query(AugmentTestResult)
        .filter(AugmentTestResult.session_id == session_id)
        .all()
    )


def clean_test_results(*, db_session, repo_id):
    return ()


def get_test_result(*, db_session, id):
    return (
        db_session.query(AugmentTestResult)
        .filter(AugmentTestResult.id == id)
        .one_or_none()
    )


def set_test_result_decision(*, db_session, user_decision: List[UserDecision]):
    for f in user_decision:
        id, decision = f.id, f.decision
        test_result = get_test_result(db_session=db_session, id=id)
        test_result.set_decision(decision)

    db_session.commit()

    return len(user_decision)


def get_session_id():
    return generate_id()
