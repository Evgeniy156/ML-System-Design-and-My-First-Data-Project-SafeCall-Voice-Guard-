"""Database initialization and seed data."""
import logging
from sqlmodel import SQLModel
from database.database import engine
from models.user import User
from models.prediction import Prediction
from auth.hash_password import HashPassword

logger = logging.getLogger(__name__)
hash_password = HashPassword()


def init_db(drop_all: bool = False):
    if drop_all:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created.")
    _seed_test_user()


def _seed_test_user():
    """Create a default test user if not exists."""
    from sqlmodel import Session, select

    with Session(engine) as session:
        existing = session.exec(
            select(User).where(User.email == "admin@safecall.ru")
        ).first()
        if not existing:
            user = User(
                email="admin@safecall.ru",
                username="admin",
                password=hash_password.create_hash("admin123"),
            )
            session.add(user)
            session.commit()
            logger.info("Seed user created: admin@safecall.ru / admin123")
