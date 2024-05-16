from src.auth.permissions import BasePermission
from src.auth.service import get_current_user

from fastapi import HTTPException

from starlette.requests import Request
from starlette.responses import Response


class TaskGetPermissions(BasePermission):
    def __init__(self, request: Request):
        try:
            user = get_current_user(request=request)
            if not user:
                raise HTTPException(
                    status_code=self.user_error_code, detail=self.user_error_msg
                )

        # this happens when the db is not set
        except AttributeError:
            pass
