"""FastAPI application with lifespan management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.firestore_client import FirestoreClient
from src.adapters.slack_client import SlackClient
from src.config.logging import configure_logging, get_logger
from src.config.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Initializes resources on startup and cleans up on shutdown.
    """
    # Startup
    settings = Settings()  # type: ignore[call-arg]
    configure_logging(json_logs=settings.LOG_JSON)
    logger = get_logger()

    logger.info(
        "Starting application",
        project_id=settings.GCP_PROJECT_ID,
        is_local=settings.is_local,
    )

    # Initialize clients
    app.state.settings = settings
    app.state.firestore = FirestoreClient(project_id=settings.GCP_PROJECT_ID)
    app.state.slack = SlackClient(token=settings.SLACK_BOT_TOKEN)

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Application shutting down")


app = FastAPI(
    title="AX Content Hub",
    description="AX(AI Transformation) 콘텐츠 큐레이션 봇",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Health status.
    """
    return {"status": "healthy"}
