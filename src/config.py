from starlette.config import Config

config = Config(".env")

COWBOY_JWT_SECRET = config("DISPATCH_JWT_SECRET", default="")
COWBOY_JWT_ALG = config("DISPATCH_JWT_ALG", default="HS256")
COWBOY_JWT_EXP = config("DISPATCH_JWT_EXP", cast=int, default=308790000)  # Seconds

OPENAI_API_KEY = config("OPENAI_API_KEY")

SQLALCHEMY_DATABASE_URI = "postgresql://cowboyuser@127.0.0.1:5432/cowboytest"
SQLALCHEMY_ENGINE_POOL_SIZE = 50

ALEMBIC_INI_PATH = "."
ALEMBIC_CORE_REVISION_PATH = "alembic"

REPOS_ROOT = "repos"

# LLM
LLM_RETRIES = 3
