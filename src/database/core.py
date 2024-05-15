import functools
import re
from typing import Annotated, Any, Union

from fastapi import Depends
from pydantic import BaseModel
from pydantic.error_wrappers import ErrorWrapper, ValidationError
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import object_session, sessionmaker, Session
from sqlalchemy.sql.expression import true
from sqlalchemy.pool import NullPool
from starlette.requests import Request

import src.config as config

engine = create_engine(
    config.SQLALCHEMY_DATABASE_URI,
    # pool_size=config.SQLALCHEMY_ENGINE_POOL_SIZE,
    # max_overflow=config.DATABASE_ENGINE_MAX_OVERFLOW,
    # pool_pre_ping=config.DATABASE_ENGINE_POOL_PING,
)


def resolve_table_name(name):
    """Resolves table names to their mapped names."""
    names = re.split("(?=[A-Z])", name)
    return "_".join([x.lower() for x in names if x])


# nested level get() function
def resolve_attr(obj, attr, default=None):
    """Attempts to access attr via dotted notation, returns none if attr does not exist."""
    try:
        return functools.reduce(getattr, attr.split("."), obj)
    except AttributeError:
        return default


class CustomBase:
    __repr_attrs__ = []
    __repr_max_length__ = 15

    # @declared_attr
    # def __tablename__(self):
    #     return resolve_table_name(self.__name__)

    def dict(self):
        """Returns a dict representation of a model."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def update(self, obj):
        """Updates a model with values from another model."""
        for key, value in obj.dict().items():
            if key in self.dict():
                setattr(self, key, value)

    @property
    def _id_str(self):
        ids = inspect(self).identity
        if ids:
            return "-".join([str(x) for x in ids]) if len(ids) > 1 else str(ids[0])
        else:
            return "None"

    @property
    def _repr_attrs_str(self):
        max_length = self.__repr_max_length__

        values = []
        single = len(self.__repr_attrs__) == 1
        for key in self.__repr_attrs__:
            if not hasattr(self, key):
                raise KeyError(
                    "{} has incorrect attribute '{}' in "
                    "__repr__attrs__".format(self.__class__, key)
                )
            value = getattr(self, key)
            wrap_in_quote = isinstance(value, str)

            value = str(value)
            if len(value) > max_length:
                value = value[:max_length] + "..."

            if wrap_in_quote:
                value = "'{}'".format(value)
            values.append(value if single else "{}:{}".format(key, value))

        return " ".join(values)

    def __repr__(self):
        # get id like '#123'
        id_str = ("#" + self._id_str) if self._id_str else ""
        # join class name, id and repr_attrs
        return "<{} {}{}>".format(
            self.__class__.__name__,
            id_str,
            " " + self._repr_attrs_str if self._repr_attrs_str else "",
        )


Base = declarative_base(cls=CustomBase)


class DBNotSetException(Exception):
    pass


def get_db(request: Request):
    try:
        return request.state.db
    except AttributeError:
        raise DBNotSetException("Database not set on request.")


# Triggers initial response field validation error
# DbSession = Annotated[Session, Depends(get_db)]
