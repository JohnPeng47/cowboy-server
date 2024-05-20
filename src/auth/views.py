from fastapi import APIRouter, Depends, HTTPException, status
from pydantic.error_wrappers import ErrorWrapper, ValidationError

from src.database.core import get_db
from sqlalchemy.orm import Session


from .models import (
    UserLogin,
    UserLoginResponse,
    UserRead,
    UserRegister,
    UserRegisterResponse,
    UserCreate,
    UserUpdate,
)
from .service import get, get_by_email, create
from .models import UserExistsError

from src.exceptions import InvalidConfigurationError


auth_router = APIRouter()


@auth_router.post("/register", response_model=UserLoginResponse)
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
