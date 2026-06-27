"""Prediction CRUD service — pattern from example MLTaskService."""
import json
from datetime import datetime
from typing import Optional, List
from sqlmodel import Session, select
from models.prediction import Prediction, TaskStatus


class PredictionService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, prediction: Prediction) -> Prediction:
        db_prediction = Prediction.model_validate(prediction)
        self.session.add(db_prediction)
        self.session.commit()
        self.session.refresh(db_prediction)
        return db_prediction

    def get(self, task_id: int) -> Optional[Prediction]:
        return self.session.get(Prediction, task_id)

    def get_all(self) -> List[Prediction]:
        return list(self.session.exec(select(Prediction)).all())

    def get_by_user(self, user_id: int) -> List[Prediction]:
        return list(
            self.session.exec(
                select(Prediction).where(Prediction.user_id == user_id)
            ).all()
        )

    def set_status(self, task_id: int, status: TaskStatus) -> Optional[Prediction]:
        prediction = self.get(task_id)
        if prediction:
            prediction.status = status
            prediction.updated_at = datetime.utcnow()
            self.session.add(prediction)
            self.session.commit()
            self.session.refresh(prediction)
        return prediction

    def set_failed(self, task_id: int, error: str) -> Optional[Prediction]:
        prediction = self.get(task_id)
        if prediction:
            prediction.status = TaskStatus.FAILED
            prediction.error_message = error[:500]
            prediction.updated_at = datetime.utcnow()
            self.session.add(prediction)
            self.session.commit()
            self.session.refresh(prediction)
        return prediction

    def set_result(self, task_id: int, result: str) -> Optional[Prediction]:
        prediction = self.get(task_id)
        if prediction:
            prediction.status = TaskStatus.COMPLETED
            prediction.result = result
            prediction.updated_at = datetime.utcnow()
            # Parse ML result JSON to fill structured fields
            try:
                ml_result = json.loads(result)
                prediction.verdict = ml_result.get("verdict")
                prediction.spoof_probability = ml_result.get("spoof_probability")
                prediction.confidence = ml_result.get("confidence")
                prediction.threshold_used = ml_result.get("threshold", 0.37)
                prediction.processing_time_ms = ml_result.get("processing_time_ms")
                prediction.model_version = ml_result.get(
                    "model_version",
                    prediction.model_version,
                )
            except (json.JSONDecodeError, AttributeError):
                pass
            self.session.add(prediction)
            self.session.commit()
            self.session.refresh(prediction)
        return prediction
