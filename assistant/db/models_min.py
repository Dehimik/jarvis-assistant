from __future__ import annotations
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import TIMESTAMP, Text, String, BigInteger, JSON
import uuid as _uuid

class Base(DeclarativeBase):
    pass

class AppLog(Base):
    __tablename__ = "app_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    level: Mapped[str] = mapped_column(String, index=True)
    logger: Mapped[Optional[str]] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    trace: Mapped[Optional[str]] = mapped_column(Text)

class CommandHistory(Base):
    __tablename__ = "command_history"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    intent: Mapped[Optional[str]] = mapped_column(String, index=True)
    slots: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    confidence: Mapped[Optional[float]]
    session_id: Mapped[Optional[_uuid.UUID]] = mapped_column(String)    # можна як UUID/string
    user_id: Mapped[Optional[_uuid.UUID]] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, index=True, default="parsed")
    error: Mapped[Optional[str]] = mapped_column(Text)
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
