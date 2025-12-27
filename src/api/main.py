"""FastAPI application with lifespan management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.firestore_client import FirestoreClient
from src.adapters.slack_client import SlackClient
from src.adapters.tasks_client import TasksClient
from src.api.internal_tasks import router as internal_tasks_router
from src.api.scheduler import router as scheduler_router
from src.api.sources import router as sources_router
from src.api.subscriptions import router as subscriptions_router
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
    app.state.tasks = TasksClient(
        mode=settings.TASKS_MODE,
        project_id=settings.GCP_PROJECT_ID,
        target_url=settings.TASKS_TARGET_URL,
        service_account_email=settings.TASKS_SERVICE_ACCOUNT_EMAIL,
    )

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

# Register routers
app.include_router(scheduler_router)
app.include_router(internal_tasks_router)
app.include_router(sources_router)
app.include_router(subscriptions_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Health status.
    """
    return {"status": "healthy"}
