from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from fastapi.exceptions import RequestValidationError
from src.core.errors import DomainError
from src.core.logger import logger


def problem_json(request: Request, *, status: int, title: str, detail: str, code: str, extra: dict | None = None):
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"https://api.example.com/errors/{code}",
            "title": title,
            "status": status,
            "detail": detail,
            "code": code,
            "instance": str(request.url),
            "extra": extra or {},
        },
    )

async def domain_error_handler(request: Request, exc: DomainError):

    logger.warning("Domain error", extra={"code": exc.code, "path": str(request.url)})
    title = exc.__class__.__name__.replace("Error", "")
    return problem_json(request, status=exc.http_status, title=title, detail=str(exc), code=exc.code, extra=exc.extra)

async def validation_error_handler(request: Request, exc: RequestValidationError):

    logger.info("Request validation error", extra={"path": str(request.url)})
    return problem_json(
        request,
        status=422,
        title="Unprocessable Entity",
        detail="Invalid request payload",
        code="request_validation_error",
        extra={"errors": exc.errors()},
    )

async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return problem_json(
        request,
        status=HTTP_500_INTERNAL_SERVER_ERROR,
        title="Internal Server Error",
        detail="Internal server error",
        code="internal_error",
    )
