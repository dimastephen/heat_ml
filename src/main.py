from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.core.error_handlers import domain_error_handler, validation_error_handler, unhandled_error_handler
from src.core.errors import DomainError
from src.core.logger import logger
from src.users.router import users_router
from src.files.router import files_router
from src.forecasts.router import forecasts_router


def create_app()->FastAPI:
    app=FastAPI(
        title=settings.APP_NAME,
        debug=settings.APP_DEBUG,
        version="0.0.1"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    app.include_router(users_router)
    app.include_router(files_router)
    app.include_router(forecasts_router)

    @app.on_event("startup")
    async def on_startup():
        logger.info(f"Starting {settings.APP_NAME} on {settings.APP_HOST}:{settings.APP_PORT}")

    @app.on_event("shutdown")
    async def on_shuthdown():
        logger.info("Application stopped")

    @app.get("/health",tags=["System"])
    async def health():
        return {"status": "GOOD"}

    return app


app = create_app()
