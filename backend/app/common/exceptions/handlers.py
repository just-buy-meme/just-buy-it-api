import traceback
import uuid
import logging
from typing import Union, Awaitable

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import HTTPStatusError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.common.exceptions.exception import (
    ApplicationException,
    BadRequestException,
    ExceptionSeverity,
    MissingPrivilegeException,
    NotFoundException,
    ValidationException,
)

logger = logging.getLogger(__name__)


def add_exception_handlers(app: FastAPI) -> None:
    # Handle custom exceptions
    app.add_exception_handler(BadRequestException, generic_exception_handler)
    app.add_exception_handler(ValidationException, generic_exception_handler)
    app.add_exception_handler(NotFoundException, generic_exception_handler)
    app.add_exception_handler(MissingPrivilegeException, generic_exception_handler)

    # Override built-in default handler
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPStatusError, http_exception_handler)

    # Fallback exception handler for all unexpected exceptions
    app.add_exception_handler(Exception, fall_back_exception_handler)


def fall_back_exception_handler(
    request: Request, exc: Exception
) -> Union[Response, Awaitable[Response]]:
    error_id = uuid.uuid4()
    traceback_string = " ".join(traceback.format_tb(exc.__traceback__))
    logger.error(
        f"Unexpected unhandled exception ({error_id}): {exc}",
        extra={
            "custom_dimensions": {"Error ID": error_id, "Traceback": traceback_string}
        },
    )
    return JSONResponse(
        content={
            "code": -1,
            "msg": f"Unexpected unhandled exception, further info ({error_id})",
            "data": f"{exc}",
        },
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def generic_exception_handler(
    request: Request, exc: Exception
) -> Union[Response, Awaitable[Response]]:  # Changed ApplicationException to Exception
    if isinstance(exc, ApplicationException):
        if exc.severity == ExceptionSeverity.CRITICAL:
            logger.critical(exc)
        elif exc.severity == ExceptionSeverity.WARNING:
            logger.warning(exc)
        else:
            logger.error(exc.data)

        return JSONResponse(
            content={
                "code": exc.code,
                "msg": exc.msg,
                "data": exc.data,
            },
            status_code=exc.code,
        )
    else:
        # Handle other exceptions
        return JSONResponse(
            content={
                "code": -1,
                "msg": "Internal Server Error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def validation_exception_handler(
    request: Request, exc: Exception
) -> Union[Response, Awaitable[Response]]:
    if isinstance(exc, RequestValidationError):
        logger.error(exc)
        return JSONResponse(
            content={
                "code": -1,
                "msg": "The received values are invalid",
                "data": {
                    "detail": exc.errors(),
                    "body": exc.body,
                },
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    else:
        # Handle other exceptions
        return JSONResponse(
            content={
                "code": -1,
                "msg": "Internal Server Error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def http_exception_handler(
    request: Request, exc: Exception
) -> Union[Response, Awaitable[Response]]:
    if isinstance(exc, HTTPStatusError):
        logger.error(exc)
        return JSONResponse(
            content={
                "code": exc.response.status_code,
                "msg": "Failed to fetch an external resource",
                "data": str(exc.response),
            },
            status_code=exc.response.status_code,
        )
    else:
        # Handle other exceptions
        return JSONResponse(
            content={
                "code": -1,
                "msg": "Internal Server Error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
