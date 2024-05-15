import logging

from typing import Annotated, Optional

from fastapi import HTTPException
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from jose.exceptions import JWKError
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED

from src.config import COWBOY_JWT_SECRET
from src.database.core import DBNotSetException, get_db


log = logging.getLogger(__name__)


from .models import CowboyUser, UserRegister, UserUpdate, UserCreate, UserLogin

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
        **user_in.dict(exclude={"password"}),
        password=password,
    )

    # projects = []
    # if user_in.projects:
    #     # we reset the default value for all user projects
    #     for user_project in user.projects:
    #         user_project.default = False

    #     for user_project in user_in.projects:
    #         projects.append(
    #             create_or_update_project_default(
    #                 db_session=db_session, user=user, user_project_in=user_project
    #             )
    #         )
    # else:
    #     # get the default project
    #     default_project = project_service.get_default_or_raise(db_session=db_session)
    #     projects.append(
    #         create_or_update_project_default(
    #             db_session=db_session,
    #             user=user,
    #             user_project_in=UserProject(
    #                 project=ProjectBase(**default_project.dict())
    #             ),
    #         )
    #     )
    # user.projects = projects

    db_session.add(user)
    db_session.commit()
    return user


#
# def get_or_create(*, db_session, user_in: UserRegister) -> CowboyUser:
#     """Gets an existing user or creates a new one."""
#     user = get_by_email(db_session=db_session, email=user_in.email)
#     if not user:
#         try:
#             user = create(db_session=db_session, user_in=user_in)
#         except IntegrityError:
#             db_session.rollback()
#             log.exception(f"Unable to create user with email address {user_in.email}.")

#     return user


def extract_user_email_jwt(request: Request, **kwargs):
    authorization: str = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer":
        log.exception(
            f"Malformed authorization header. Scheme: {scheme} Param: {param} Authorization: {authorization}"
        )
        return

    token = authorization.split()[1]

    try:
        data = jwt.decode(token, COWBOY_JWT_SECRET)
    except (JWKError, JWTError):
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
    print(user_email)

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
