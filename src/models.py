from datetime import datetime
from sqlalchemy import Column, DateTime, event
from pydantic import BaseModel, Field
from pydantic.types import SecretStr

from typing import Annotated

PrimaryKey = Annotated[int, Field(gt=0, lt=2147483647)]
NameStr = Annotated[
    str, Field(pattern=r"^(?!\s*$).+", strip_whitespace=True, min_length=3)
]


class TimeStampMixin(object):
    """Timestamping mixin"""

    created_at = Column(DateTime, default=datetime.utcnow)
    created_at._creation_order = 9998
    updated_at = Column(DateTime, default=datetime.utcnow)
    updated_at._creation_order = 9998

    @staticmethod
    def _updated_at(mapper, connection, target):
        target.updated_at = datetime.utcnow()

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, "before_update", cls._updated_at)


class CowboyBase(BaseModel):
    class Config:
        from_attributes = True
        validate_assignment = True
        arbitrary_types_allowed = True
        str_strip_whitespace = True

        json_encoders = {
            # custom output conversion for datetime
            datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M:%SZ") if v else None,
            SecretStr: lambda v: v.get_secret_value() if v else None,
        }


class HTTPSuccess(BaseModel):
    msg: str = "Success"
