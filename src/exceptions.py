from pydantic.errors import PydanticUserError


class CowboyRunTimeException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
