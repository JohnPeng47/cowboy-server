from fastapi import APIRouter, Depends, HTTPException, status
from src.database.core import Session, get_db
from src.auth.service import get_current_user, CowboyUser

from pydantic.error_wrappers import ErrorWrapper, ValidationError


from .service import create, get, delete
from .models import RepoConfig, RepoConfigCreate

from src.exceptions import InvalidConfigurationError
from src.models import HTTPSuccess

repo_router = APIRouter()


@repo_router.post("/repo/create", response_model=RepoConfigCreate)
def create_repo(
    repo_in: RepoConfigCreate,
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
):
    repo = get(
        db_session=db_session, repo_name=repo_in.repo_name, curr_user=current_user
    )
    if repo:
        raise ValidationError(
            [
                ErrorWrapper(
                    InvalidConfigurationError(
                        msg="A repo with this name already exists."
                    ),
                    loc="repo_name",
                )
            ],
            model=RepoConfigCreate,
        )

    repo = create(db_session=db_session, repo_in=repo_in, curr_user=current_user)

    # need as_dict to convert cloned_folders to list
    return repo.as_dict()


@repo_router.delete("/repo/delete/{repo_name}", response_model=HTTPSuccess)
def delete_repo(
    repo_name: str,
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
):
    repo = delete(db_session=db_session, repo_name=repo_name, curr_user=current_user)
    if not repo:
        raise ValidationError(
            [
                ErrorWrapper(
                    InvalidConfigurationError(
                        msg="A repo with this name does not exist."
                    ),
                    loc="repo_name",
                )
            ],
            model=RepoConfigCreate,
        )
    return HTTPSuccess()
