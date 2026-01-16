from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.database import get_db
from app.models import Telemetry, Position
from app.schemas import TelemetryResponse, PositionResponse

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("", response_model=List[TelemetryResponse])
async def get_telemetry(
    node_id: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get telemetry data."""
    query = select(Telemetry).order_by(Telemetry.timestamp.desc())

    if node_id:
        query = query.where(Telemetry.node_id == node_id)

    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    node_id: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get position history."""
    query = select(Position).order_by(Position.timestamp.desc())

    if node_id:
        query = query.where(Position.node_id == node_id)

    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
