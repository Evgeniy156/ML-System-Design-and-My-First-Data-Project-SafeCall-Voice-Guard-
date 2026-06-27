"""User CRUD operations."""
from typing import Optional
from sqlmodel import Session, select
from models.user import User


def get_user_by_email(email: str, session: Session) -> Optional[User]:
    return session.exec(select(User).where(User.email == email)).first()


def create_user(user: User, session: Session) -> User:
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
