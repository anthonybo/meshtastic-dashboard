from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Node(Base):
    __tablename__ = "nodes"

    id = Column(String, primary_key=True)  # e.g., "!9e9f2d30"
    num = Column(Integer, unique=True, index=True)
    long_name = Column(String, nullable=True)
    short_name = Column(String, nullable=True)
    mac_addr = Column(String, nullable=True)
    hw_model = Column(String, nullable=True)
    role = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Integer, nullable=True)
    battery_level = Column(Integer, nullable=True)
    voltage = Column(Float, nullable=True)
    snr = Column(Float, nullable=True)
    hops_away = Column(Integer, nullable=True)
    last_heard = Column(DateTime, nullable=True)
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # No FK constraint - we may receive messages from unknown nodes or send from our own node before it's synced
    from_node_id = Column(String, nullable=True)
    to_node_id = Column(String, nullable=True)  # Can be broadcast
    channel = Column(Integer, default=0)
    text = Column(Text)
    timestamp = Column(DateTime, server_default=func.now())
    is_outgoing = Column(Boolean, default=False)
    ack_received = Column(Boolean, default=False)
    ack_failed = Column(Boolean, default=False)  # True if NAK received
    ack_error = Column(String, nullable=True)  # Error reason if failed


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(String, ForeignKey("nodes.id"), index=True)
    battery_level = Column(Integer, nullable=True)
    voltage = Column(Float, nullable=True)
    channel_utilization = Column(Float, nullable=True)
    air_util_tx = Column(Float, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)
    timestamp = Column(DateTime, server_default=func.now())


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(String, ForeignKey("nodes.id"), index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Integer, nullable=True)
    timestamp = Column(DateTime, server_default=func.now())
