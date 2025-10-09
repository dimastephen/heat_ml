from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.core.logger import logger


def create_app()->FastAPI:
    app=FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        version="0.0.1"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

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

