from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def make_engine(dsn: str):
    """
    Створює SQLAlchemy Engine.
    dsn — рядок підключення типу:
      postgresql+psycopg2://user:password@localhost:5432/jarvis
      або sqlite:///jarvis.db
    """
    return create_engine(
        dsn,
        pool_pre_ping=True,     # автоматично перевіряє з’єднання
        future=True
    )

def make_session_factory(dsn: str):
    """
    Повертає фабрику сесій (sessionmaker), з якої потім
    створюються сесії через:
        SF = make_session_factory(dsn)
        with SF() as db:
            ...
    """
    engine = make_engine(dsn)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
