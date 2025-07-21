import logging

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException as http_exception:
            logger.error(
                f"HTTPException: {http_exception.status_code} - {http_exception.detail}"
            )
            return JSONResponse(
                status_code=http_exception.status_code,
                content={
                    "code": -1,
                    "msg": str(http_exception.detail),
                    "data": "",
                },
            )
        except Exception as e:
            logger.error(f"Exception: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"code": -1, "msg": "Internal Server Error", "data": str(e)},
            )
