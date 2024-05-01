from starlette.config import Config

config = Config(".env")

COWBOY_JWT_SECRET = config("DISPATCH_JWT_SECRET", default="")
COWBOY_JWT_ALG = config("DISPATCH_JWT_ALG", default="HS256")
COWBOY_JWT_EXP = config("DISPATCH_JWT_EXP", cast=int, default=308790000)  # Seconds


SQLALCHEMY_DATABASE_URI = (
    "postgresql://postgres:my_password@127.0.0.1:8082/cowboy_local"
)
SQLALCHEMY_ENGINE_POOL_SIZE = 50


ALEMBIC_INI_PATH = "."
ALEMBIC_CORE_REVISION_PATH = "alembic"

REPOS_ROOT = "repos"
