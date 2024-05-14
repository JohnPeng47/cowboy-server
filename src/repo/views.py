from fastapi import APIRouter, Depends
from src.database.core import Session, get_db
from src.exceptions import InvalidConfigurationError
from src.models import HTTPSuccess

from pydantic.error_wrappers import ErrorWrapper, ValidationError

from src.auth.service import get_current_user, CowboyUser
from src.test_modules.service import create_all_tms

from .service import create_or_update, get, delete, list, clean
from .models import RepoConfigCreate, RepoConfigList, RepoConfigGet

repo_router = APIRouter()


# also create the test_modules here as well
# and nodes
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

    repo_config = create_or_update(
        db_session=db_session, repo_in=repo_in, curr_user=current_user
    )
    # need as_dict to convert cloned_folders to list
    return repo_config.to_dict()


@repo_router.delete("/repo/delete/{repo_name}", response_model=HTTPSuccess)
def delete_repo(
    repo_name: str,
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
):
    deleted = delete(db_session=db_session, repo_name=repo_name, curr_user=current_user)

    if not deleted:
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


@repo_router.delete("/repo/clean/{repo_name}", response_model=HTTPSuccess)
def clean_repo(
    repo_name: str,
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
):
    cleaned = clean(db_session=db_session, repo_name=repo_name, curr_user=current_user)

    if not cleaned:
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


@repo_router.get("/repo/get/{repo_name}", response_model=RepoConfigGet)
def get_repo(
    repo_name: str,
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
):
    repo = get(db_session=db_session, repo_name=repo_name, curr_user=current_user)
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
            model=RepoConfigGet,
        )

    return repo.to_dict()


@repo_router.get("/repo/list", response_model=RepoConfigList)
def list_repos(
    db_session: Session = Depends(get_db),
    current_user: CowboyUser = Depends(get_current_user),
):
    repos = list(db_session=db_session, curr_user=current_user)
    return RepoConfigList(repo_list=repos)
