from src.database.core import get_db
from src.auth.models import CowboyUser
from src.models import HTTPSuccess
from src.exceptions import InvalidConfigurationError

from .service import get_current_user, get, get_by_email, create, store_oai_key
from .models import UserLoginResponse, UserRegister, UpdateOAIKey

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic.error_wrappers import ErrorWrapper, ValidationError
from sqlalchemy.orm import Session


auth_router = APIRouter()


@auth_router.post("/user/register", response_model=UserLoginResponse)
def register_user(
    user_in: UserRegister,
    db_session: Session = Depends(get_db),
):
    user = get_by_email(db_session=db_session, email=user_in.email)
    if user:
        raise ValidationError(
            [
                ErrorWrapper(
                    InvalidConfigurationError(
                        msg="A user with this email already exists."
                    ),
                    loc="email",
                )
            ],
            model=UserRegister,
        )

    user = create(db_session=db_session, user_in=user_in)
    return user


@auth_router.get("/user/delete")
def delete_user(
    curr_user: CowboyUser = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    user = get(db_session=db_session, user_id=curr_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db_session.delete(user)
    db_session.commit()

    return HTTPSuccess()


@auth_router.post("/user/update/openai-key")
def update_oai_key(
    request: UpdateOAIKey,
    curr_user: CowboyUser = Depends(get_current_user),
    db_session: Session = Depends(get_db),
):
    user = get(db_session=db_session, user_id=curr_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    store_oai_key(user_id=user.id, api_key=request.openai_api_key)

    return HTTPSuccess()
