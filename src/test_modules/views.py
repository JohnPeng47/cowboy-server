from fastapi import APIRouter, Depends, HTTPException, status
from src.database.core import Session, get_db
from src.auth.service import get_current_user, CowboyUser

from pydantic.error_wrappers import ErrorWrapper, ValidationError

from src.models import HTTPSuccess
from src.repo.service import get as get_repoconf

from .models import GetTargetCovRequest
from .service import get_tgt_coverage


tm_router = APIRouter()


@tm_router.post("/tm/target_coverage")
def get_tm_target_coverage(
    request: GetTargetCovRequest,
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
):
    repo_conf = get_repoconf(
        db_session=db_session, curr_user=current_user, repo_name=request.repo_name
    )

    return HTTPSuccess()
