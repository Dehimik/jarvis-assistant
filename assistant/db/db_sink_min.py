import sys
from loguru import logger
from sqlalchemy.orm import sessionmaker
from .repo_min import insert_log

class DBSink:
    def __init__(self, SessionFactory: sessionmaker):
        self._sf = SessionFactory

    def __call__(self, message):
        record = message.record
        try:
            with self._sf() as db:
                insert_log(
                    db,
                    level=record["level"].name,
                    logger=record["name"],
                    message=record["message"],
                    context=dict(record.get("extra", {})) or None,
                    trace=str(record["exception"].traceback) if record.get("exception") else None
                )
                db.commit()
        except Exception as e:
            # ВАЖЛИВО: Не можна "ковтати" помилки мовчки.
            # Якщо запис в лог падає, ми маємо про це знати.
            # Пишемо в stderr, щоб уникнути нескінченного циклу логування.
            print(f"ПОМИЛКА [DBSink]: Не вдалося записати лог в БД: {e}", file=sys.stderr)
            # Можна також вивести оригінальний запис, який не зберігся
            print(f"  > РІВЕНЬ: {record['level'].name}, ЛОГЕР: {record['name']}", file=sys.stderr)
            print(f"  > ПОВІДОМЛЕННЯ: {record['message']}", file=sys.stderr)