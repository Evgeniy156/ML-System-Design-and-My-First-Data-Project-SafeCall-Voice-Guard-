"""Database engine and session — pattern from example/app/database/database.py."""
from sqlmodel import SQLModel, Session, create_engine
from database.config import get_settings


def get_database_engine():
    settings = get_settings()
    return create_engine(
        url=settings.DATABASE_URL_psycopg,
        echo=settings.DEBUG,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


engine = get_database_engine()


def get_session():
    with Session(engine) as session:
        yield session
