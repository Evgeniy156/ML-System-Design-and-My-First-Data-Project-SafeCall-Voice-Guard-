"""Prediction domain model — TaskStatus enum + to_queue_message() pattern from example."""
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from models.user import User


class TaskStatus(str, Enum):
    NEW = "new"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PredictionBase(SQLModel):
    status: TaskStatus = Field(default=TaskStatus.NEW)
    result: Optional[str] = Field(default=None)
    audio_filename: Optional[str] = Field(default=None, max_length=500)


class Prediction(PredictionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    verdict: Optional[str] = Field(default=None, max_length=20)
    spoof_probability: Optional[float] = None
    confidence: Optional[float] = None
    threshold_used: float = 0.37
    processing_time_ms: Optional[float] = None
    model_version: str = "xlsr-53-head-v1"
    error_message: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    creator: Optional["User"] = Relationship(
        back_populates="predictions",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    def to_queue_message(self) -> dict:
        """Serialize task for RabbitMQ — pattern from example MLTask."""
        return {
            "task_id": self.id,
            "audio_filename": self.audio_filename,
        }


class PredictionCreate(PredictionBase):
    audio_filename: str
    user_id: int
    status: TaskStatus = TaskStatus.NEW


class PredictionUpdate(PredictionBase):
    status: Optional[TaskStatus] = None
    result: Optional[str] = None
