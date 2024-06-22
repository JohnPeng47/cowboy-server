import logging

from typing import Optional

from fastapi import HTTPException
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from jose.exceptions import JWKError
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED

from src.config import COWBOY_JWT_SECRET
from src.database.core import DBNotSetException, get_db

from .models import generate_token


log = logging.getLogger(__name__)

from .sm import SecretManager
from .models import CowboyUser, UserRegister, UserCreate

InvalidCredentialException = HTTPException(
    status_code=HTTP_401_UNAUTHORIZED,
    detail=[{"msg": "Could not validate credentials"}],
)


def get(*, db_session, user_id: int) -> Optional[CowboyUser]:
    """Returns a user based on the given user id."""
    return db_session.query(CowboyUser).filter(CowboyUser.id == user_id).one_or_none()


def get_by_email(*, db_session, email: str) -> Optional[CowboyUser]:
    """Returns a user object based on user email."""
    return db_session.query(CowboyUser).filter(CowboyUser.email == email).one_or_none()


def create(*, db_session, user_in: UserRegister | UserCreate) -> CowboyUser:
    """Creates a new dispatch user."""
    # pydantic forces a string password, but we really want bytes
    password = bytes(user_in.password, "utf-8")

    # create the user
    user = CowboyUser(
        **user_in.dict(exclude={"password", "openai_api_key"}),
        password=password,
    )
    db_session.add(user)
    db_session.commit()

    # create the credentials
    store_oai_key(user_in.openai_api_key, user.id)

    return user


def get_user_token(*, db_session, user_id):
    user = get(db_session=db_session, user_id=user_id)
    return generate_token(user.email)


def extract_user_email_jwt(request: Request, **kwargs):
    try:
        authorization: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            log.exception(
                f"Malformed authorization header. Scheme: {scheme} Param: {param} Authorization: {authorization}"
            )
            return

        token = authorization.split()[1]
        data = jwt.decode(token, COWBOY_JWT_SECRET)
    except (JWKError, JWTError, IndexError, KeyError):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=[{"msg": "Could not validate credentials"}],
        ) from None
    return data["email"]


# def get_current_user(request: Request) -> CowboyUser:
#     user_email = extract_user_email_jwt(request=request)

#     if not user_email:
#         log.exception(f"Failed to extract user email")
#         raise InvalidCredentialException

#     # kinda of strange ... if user exists, we generate a random password
#     # for the user here ...
#     return get_or_create(
#         db_session=request.state.db,
#         user_in=UserRegister(email=user_email),
#     )


def get_current_user(request: Request) -> CowboyUser:
    user_email = extract_user_email_jwt(request=request)

    if not user_email:
        log.exception(f"Failed to extract user email")
        raise InvalidCredentialException

    # kinda of strange ... if user exists, we generate a random password
    # for the user here ...
    try:
        user = get_by_email(
            db_session=get_db(request),
            email=user_email,
        )
    # this is special case for requests polling the /task/get endpoint
    # where we are not passed a db session, and we want to proceed with the rest
    # of endpoint logic
    except DBNotSetException:
        print("No db set")
        return None

    # generic case for user not existing
    if not user:
        print("No user")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail=[{"msg": "User not found"}]
        )

    return user


def store_oai_key(api_key, user_id):
    sm = SecretManager()
    sm.store_parameter("OAI_KEY_" + str(user_id), api_key)


def retrieve_oai_key(user_id):
    sm = SecretManager()
    return sm.retrieve_parameter("OAI_KEY_" + str(user_id))
