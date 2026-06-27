"""User domain model."""
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from models.prediction import Prediction


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    username: str = Field(max_length=50)


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    password: str = Field(max_length=255)
    predictions: List["Prediction"] = Relationship(back_populates="creator")


class UserCreate(UserBase):
    password: str
