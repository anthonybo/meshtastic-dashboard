import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import nodes, messages, telemetry, connection, websocket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Meshtastic Dashboard API...")
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
