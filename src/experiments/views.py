from src.database.core import get_db
from src.auth.service import get_current_user, CowboyUser
from src.repo.service import get_experiment
from src.test_modules.service import get_tms_by_names

from .models import ExperimentRequest
from .augment_test import run_experiment

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session


exp_router = APIRouter()


@exp_router.post("/experiment/create")
def create_experiment(
    exp_config: ExperimentRequest,
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
):
    repo = get_experiment(
        db_session=db_session, curr_user=current_user, repo_name=exp_config.repo_name
    )
    tm_models = get_tms_by_names(
        db_session=db_session, repo_id=repo.id, tm_names=exp_config.tms
    )

    run_experiment(
        repo=repo,
        test_modules=tm_models,
        to_keep=int(exp_config.to_keep),
        to_delete=int(exp_config.to_delete),
    )
