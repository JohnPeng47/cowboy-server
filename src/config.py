from starlette.config import Config

from enum import Enum

config = Config(".env")

COWBOY_JWT_SECRET = config("DISPATCH_JWT_SECRET", default="")
COWBOY_JWT_ALG = config("DISPATCH_JWT_ALG", default="HS256")
COWBOY_JWT_EXP = config("DISPATCH_JWT_EXP", cast=int, default=308790000)  # Seconds

COWBOY_OPENAI_API_KEY = config("OPENAI_API_KEY")

DB_PASS = config("DB_PASS")
SQLALCHEMY_DATABASE_URI = (
    f"postgresql://cowboyuser2:{DB_PASS}@127.0.0.1:5432/cowboytest3"
)
SQLALCHEMY_ENGINE_POOL_SIZE = 50

ALEMBIC_INI_PATH = "."
ALEMBIC_CORE_REVISION_PATH = "alembic"

# LLM settings
LLM_RETRIES = 3

AUTO_GEN_SIZE = 7

LOG_DIR = "log"

REPOS_ROOT = "repos"

AWS_REGION = "us-east-2"


class Language(str, Enum):
    """
    Currently supported languages
    """

    python = "python"
