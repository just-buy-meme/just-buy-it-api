from enum import Enum
from typing import Any, Dict, Union

from fastapi import HTTPException
from pydantic import BaseModel
from starlette import status as request_status


class ExceptionSeverity(Enum):
    WARNING = 1
    ERROR = 2
    CRITICAL = 3


class ErrorResponse(BaseModel):
    code: int = 500
    msg: str = "The requested operation failed"
    data: str = "An unknown and unhandled exception occurred in the API"


class ApplicationException(Exception):
    code: int = 500
    severity: ExceptionSeverity = ExceptionSeverity.ERROR
    msg: str = "The requested operation failed"
    data: str = "An unknown and unhandled exception occurred in the API"
    extra: Union[Dict[str, Any], None] = None

    def __init__(
        self,
        msg: str = "The requested operation failed",
        data: str = "An unknown and unhandled exception occurred in the API",
        extra: Union[Dict[str, Any], None] = None,
        code: int = 500,
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
    ):
        self.code = code
        self.msg = msg
        self.data = data
        self.extra = extra
        self.severity = severity

    def dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "msg": self.msg,
            "data": self.data,
            "extra": self.extra,
        }


class MissingPrivilegeException(ApplicationException):
    def __init__(
        self,
        msg: str = "You do not have the required permissions",
        data: str = "Action denied because of insufficient permissions",
        extra: Union[Dict[str, Any], None] = None,
    ):
        super().__init__(
            msg,
            data,
            extra,
            request_status.HTTP_403_FORBIDDEN,
            severity=ExceptionSeverity.WARNING,
        )


class NotFoundException(ApplicationException):
    def __init__(
        self,
        msg: str = "The requested resource could not be found",
        data: str = "The requested resource could not be found",
        extra: Union[Dict[str, Any], None] = None,
    ):
        super().__init__(msg, data, extra, request_status.HTTP_404_NOT_FOUND)


class BadRequestException(ApplicationException):
    def __init__(
        self,
        msg: str = "Invalid data for the operation",
        data: str = "Unable to complete the requested operation with the given input values.",
        extra: Union[Dict[str, Any], None] = None,
    ):
        super().__init__(msg, data, extra, request_status.HTTP_400_BAD_REQUEST)


class ValidationException(ApplicationException):
    def __init__(
        self,
        msg: str = "The received data is invalid",
        data: Any = "Values are invalid for requested operation.",
        extra: Union[Dict[str, Any], None] = None,
    ):
        super().__init__(msg, data, extra, request_status.HTTP_422_UNPROCESSABLE_ENTITY)


credentials_exception = HTTPException(
    status_code=request_status.HTTP_401_UNAUTHORIZED,
    detail="Token validation failed",
    headers={"WWW-Authenticate": "Bearer"},
)
