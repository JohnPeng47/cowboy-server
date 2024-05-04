from pydantic.errors import PydanticValueError


class InvalidConfigurationError(PydanticValueError):
    code = "invalid.configuration"
    msg_template = "{msg}"


class CowboyRunTimeException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
