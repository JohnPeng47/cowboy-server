from src.config import COWBOY_JWT_ALG, COWBOY_JWT_EXP, COWBOY_JWT_SECRET
from src.database.core import Base
from src.models import TimeStampMixin, CowboyBase, PrimaryKey

import string
import secrets
import bcrypt
from jose import jwt
from typing import Optional
from pydantic import validator, Field, BaseModel
from pydantic.networks import EmailStr
from sqlalchemy import DateTime, Column, String, LargeBinary, Integer, Boolean
from typing import List
from datetime import datetime, timedelta


def generate_password():
    """Generates a reasonable password if none is provided."""
    alphanumeric = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphanumeric) for i in range(10))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)  # noqa
            and sum(c.isdigit() for c in password) >= 3  # noqa
        ):
            break
    return password


def hash_password(password: str):
    """Generates a hashed version of the provided password."""
    pw = bytes(password, "utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw, salt)


class CowboyUser(Base, TimeStampMixin):
    __tablename__ = "cowboy_user"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password = Column(LargeBinary, nullable=False)
    last_mfa_time = Column(DateTime, nullable=True)
    experimental_features = Column(Boolean, default=False)

    # repos = relationship("Repo", backref="cowboy_user")

    # search_vector = Column(
    #     TSVectorType("email", regconfig="pg_catalog.simple", weights={"email": "A"})
    # )

    def check_password(self, password):
        return bcrypt.checkpw(password.encode("utf-8"), self.password)

    @property
    def token(self):
        now = datetime.utcnow()
        exp = (now + timedelta(seconds=COWBOY_JWT_EXP)).timestamp()
        data = {
            "exp": exp,
            "email": self.email,
        }
        return jwt.encode(data, COWBOY_JWT_SECRET, algorithm=COWBOY_JWT_ALG)


class UserBase(CowboyBase):
    email: EmailStr

    @validator("email")
    def email_required(cls, v):
        if not v:
            raise ValueError("Must not be empty string and must be a email")
        return v


class UserLogin(UserBase):
    password: str

    @validator("password")
    def password_required(cls, v):
        if not v:
            raise ValueError("Must not be empty string")
        return v


class UserRegister(UserLogin):
    openai_api_key: str
    password: Optional[str] = Field(None, nullable=True)

    @validator("password", pre=True, always=True)
    def password_required(cls, v):
        # we generate a password for those that don't have one
        password = v or generate_password()
        return hash_password(password)


class UserLoginResponse(CowboyBase):
    token: Optional[str] = Field(None, nullable=True)


class UserRead(UserBase):
    id: PrimaryKey
    role: Optional[str] = Field(None, nullable=True)
    experimental_features: Optional[bool]


class UserUpdate(CowboyBase):
    id: PrimaryKey
    password: Optional[str] = Field(None, nullable=True)

    @validator("password", pre=True)
    def hash(cls, v):
        return hash_password(str(v))


class UserCreate(CowboyBase):
    email: EmailStr
    password: Optional[str] = Field(None, nullable=True)

    @validator("password", pre=True)
    def hash(cls, v):
        return hash_password(str(v))


class UserRegisterResponse(CowboyBase):
    token: Optional[str] = Field(None, nullable=True)


# Errors
class UserExistsError(BaseModel):
    error = "User already exists"
