from typing import Optional, Final
from contextvars import ContextVar

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic.error_wrappers import ValidationError

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from sqlalchemy.orm import sessionmaker

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

import uvicorn
from logging import getLogger
from src.logger import configure_uvicorn_logger
import yaml
import threading

from src.queue.core import TaskQueue
from src.auth.views import auth_router
from src.repo.views import repo_router
from src.test_modules.views import tm_router
from src.queue.views import task_queue_router
from src.test_gen.views import test_gen_router
from src.target_code.views import tgtcode_router
from src.experiments.views import exp_router
from src.exceptions import CowboyRunTimeException
from src.database.core import engine
from src.threads import check_for_changed_files

import uuid


# import logfire

log = getLogger(__name__)


# def disable_uvicorn_logging():
#     uvicorn_error = logging.getLogger("uvicorn.error")
#     uvicorn_error.disabled = True
#     uvicorn_access = logging.getLogger("uvicorn.access")
#     uvicorn_access.disabled = True


async def not_found(request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": [{"msg": "Not Found."}]},
    )


exception_handlers = {404: not_found}


app = FastAPI(exception_handlers=exception_handlers, openapi_url="/docs/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# def get_path_params_from_request(request: Request) -> str:
#     path_params = {}
#     for r in api_router.routes:
#         path_regex, path_format, param_converters = compile_path(r.path)
#         path = request["path"].removeprefix(
#             "/api/v1"
#         )  # remove the /api/v1 for matching
#         match = path_regex.match(path)
#         if match:
#             path_params = match.groupdict()
#     return path_params


def get_path_template(request: Request) -> str:
    if hasattr(request, "path"):
        return ",".join(request.path.split("/")[1:])
    return ".".join(request.url.path.split("/")[1:])


REQUEST_ID_CTX_KEY: Final[str] = "request_id"
_request_id_ctx_var: ContextVar[Optional[str]] = ContextVar(
    REQUEST_ID_CTX_KEY, default=None
)


def get_request_id() -> Optional[str]:
    return _request_id_ctx_var.get()


# these paths do not require DB
NO_DB_PATHS = ["/task/get"]


class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StreamingResponse:
        try:
            response = await call_next(request)
        except ValidationError as e:
            log.exception(e)
            response = JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": e.errors(), "error": True},
            )
        except ValueError as e:
            log.exception(e)
            response = JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": [
                        {"msg": "Unknown", "loc": ["Unknown"], "type": "Unknown"}
                    ],
                    "error": True,
                },
            )
        except CowboyRunTimeException as e:
            log.exception(e)
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": [{"msg": f"Runtime error: {e.message}"}],
                    "error": True,
                },
            )
        except Exception as e:
            log.exception(e)
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": [
                        {"msg": "Unknown", "loc": ["Unknown"], "type": "Unknown"}
                    ],
                    "error": True,
                },
            )

        return response


token_registry = []


class DBMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # request_id = str(uuid1())

        # we create a per-request id such that we can ensure that our session is scoped for a particular request.
        # see: https://github.com/tiangolo/fastapi/issues/726
        # ctx_token = _request_id_ctx_var.set(request_id)
        # path_params = get_path_params_from_request(request)

        # # if this call is organization specific set the correct search path
        # organization_slug = path_params.get("organization", "default")
        # request.state.organization = organization_slug

        # # Find out more about
        # schema = f"dispatch_organization_{organization_slug}"
        # # validate slug exists
        # schema_names = inspect(engine).get_schema_names()
        # if schema in schema_names:
        #     # add correct schema mapping depending on the request
        #     schema_engine = engine.execution_options(
        #         schema_translate_map={
        #             None: schema,
        #         }
        #     )
        # else:
        #     return JSONResponse(
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #         content={"detail": [{"msg": f"Unknown database schema name: {schema}"}]},
        #     )

        try:
            # can't do this because every request needs access to user auth which reuqires db
            # if request.url.path in NO_DB_PATHS:
            #     print("Skipping for path: ", request.url.path)
            #     return call_next(request)

            # this is a very janky implementation to handle the fact that assigning a db session
            # to every request blows up our db connection pool
            task_auth_token = request.headers.get("x-task-auth")
            if not task_auth_token in token_registry:
                print("No token in registry: ", task_auth_token, token_registry)
                print(
                    type(task_auth_token),
                    type(token_registry[0]) if len(token_registry) > 0 else "oigneng",
                )
                session = sessionmaker(bind=engine)
                request.state.db = session()
                request.state.db.id = str(uuid.uuid4())

            response = await call_next(request)
        except Exception as e:
            raise e from None
        finally:
            db = getattr(request.state, "db", None)
            if db:
                db.close()

        # _request_id_ctx_var.reset(ctx_token)
        return response


class AddTaskQueueMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.task_queue = TaskQueue()
        response = await call_next(request)
        return response


app.add_middleware(ExceptionMiddleware)
app.add_middleware(DBMiddleware)
app.add_middleware(AddTaskQueueMiddleware)

app.include_router(auth_router)
app.include_router(repo_router)
app.include_router(tm_router)
app.include_router(task_queue_router)
app.include_router(test_gen_router)
app.include_router(tgtcode_router)
app.include_router(exp_router)

# starts threads to check for repo updates
Session = sessionmaker(bind=engine)
db_session = Session()
threading.Thread(
    target=check_for_changed_files, args=(db_session,), daemon=True
).start()

# logfire.configure(console=False)
# logfire.instrument_fastapi(app)

if __name__ == "__main__":
    uvicorn_version = uvicorn.__version__

    # doesnt work ??
    configure_uvicorn_logger()

    with open("uvicorn.yaml", "r") as f:
        config = yaml.safe_load(f)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3000,
        # reload=True,
        reload_excludes=["./repos"],
        # log_config=config,
    )
