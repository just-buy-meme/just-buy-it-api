from typing import Any, Dict, Union

from app.common.exceptions.exception import (
    ApplicationException,
    BadRequestException,
    ErrorResponse,
    MissingPrivilegeException,
    NotFoundException,
    ValidationException,
)

responses: Dict[Union[int, str], Dict[str, Any]] = {
    400: {
        "model": ErrorResponse,
        "content": {"application/json": {"example": BadRequestException().dict()}},
    },
    401: {
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": ErrorResponse(
                    code=-1,
                    msg="UnauthorizedException",
                    data="Token validation failed",
                ).dict()
            }
        },
    },
    403: {
        "model": ErrorResponse,
        "content": {
            "application/json": {"example": MissingPrivilegeException().dict()}
        },
    },
    404: {
        "model": ErrorResponse,
        "content": {"application/json": {"example": NotFoundException().dict()}},
    },
    422: {
        "model": ErrorResponse,
        "content": {"application/json": {"example": ValidationException().dict()}},
    },
    500: {
        "model": ErrorResponse,
        "content": {"application/json": {"example": ApplicationException().dict()}},
    },
}
