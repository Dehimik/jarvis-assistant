from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .models_min import AppLog, CommandHistory

def now_utc():
    return datetime.now(timezone.utc)

def insert_log(db: Session, level: str, logger: str, message: str, context: dict | None = None, trace: str | None = None):
    log = AppLog(
        created_at=now_utc(),
        level=level,
        logger=logger,
        message=message,
        context=context or None,
        trace=trace
    )
    db.add(log)
    db.flush()
    return log.id

def insert_command_event(
    db: Session,
    raw_text: str | None = None,
    intent: str | None = None,
    slots: dict | None = None,
    confidence: float | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    status: str = "parsed",
    error: str | None = None,
    meta: dict | None = None,
):
    ev = CommandHistory(
        created_at=now_utc(),
        raw_text=raw_text,
        intent=intent,
        slots=slots or None,
        confidence=confidence,
        session_id=session_id,
        user_id=user_id,
        status=status,
        error=error,
        meta=meta or None
    )
    db.add(ev)
    db.flush()
    return ev.id
