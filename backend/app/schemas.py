from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NodeBase(BaseModel):
    id: str
    num: int
    long_name: Optional[str] = None
    short_name: Optional[str] = None
    hw_model: Optional[str] = None
    role: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[int] = None
    battery_level: Optional[int] = None
    voltage: Optional[float] = None
    snr: Optional[float] = None
    hops_away: Optional[int] = None
    last_heard: Optional[datetime] = None
    is_favorite: bool = False


class NodeResponse(NodeBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    text: str
    to_node_id: Optional[str] = None  # None = broadcast
    channel: int = 0


class MessageResponse(BaseModel):
    id: int
    from_node_id: Optional[str] = None
    to_node_id: Optional[str] = None
    channel: int
    text: str
    timestamp: datetime
    is_outgoing: bool
    ack_received: bool
    ack_failed: bool = False
    ack_error: Optional[str] = None

    class Config:
        from_attributes = True


class TelemetryResponse(BaseModel):
    id: int
    node_id: str
    battery_level: Optional[int] = None
    voltage: Optional[float] = None
    channel_utilization: Optional[float] = None
    air_util_tx: Optional[float] = None
    uptime_seconds: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    id: int
    node_id: str
    latitude: float
    longitude: float
    altitude: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ConnectionStatus(BaseModel):
    connected: bool
    device_name: Optional[str] = None
    my_node_num: Optional[int] = None
    firmware_version: Optional[str] = None
    hw_model: Optional[str] = None


class WebSocketMessage(BaseModel):
    type: str  # "message", "node_update", "telemetry", "position", "connection"
    data: dict
