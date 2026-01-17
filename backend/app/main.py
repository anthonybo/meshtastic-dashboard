import logging
import os
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import nodes, messages, telemetry, connection, websocket

# Configure logging with file output
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "meshtastic_dashboard.log")

# Create formatter with clear labels
log_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# File handler with rotation: 5MB max size, keep 1 backup (total 10MB max)
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=1,  # Keep 1 backup file
    encoding="utf-8"
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)  # Capture everything to file

# Console handler for terminal output
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)  # Less verbose for console

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Reduce noise from third-party libraries
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("bleak").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("=" * 60)
    logger.info("Starting Meshtastic Dashboard API...")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("=" * 60)
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Meshtastic Dashboard API",
    description="API for monitoring and controlling Meshtastic devices",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(nodes.router)
app.include_router(messages.router)
app.include_router(telemetry.router)
app.include_router(connection.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {"message": "Meshtastic Dashboard API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
