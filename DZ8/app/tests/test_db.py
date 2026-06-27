"""Database model tests."""
from models.user import User
from models.prediction import Prediction, TaskStatus


def test_create_user(session):
    user = User(email="test@test.ru", username="tester", password="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)
    assert user.id is not None
    assert user.email == "test@test.ru"


def test_create_prediction(session):
    # Create user first
    user = User(email="pred@test.ru", username="pred", password="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)

    prediction = Prediction(
        audio_filename="/test/audio.wav",
        user_id=user.id,
        status=TaskStatus.NEW,
        threshold_used=0.37,
        model_version="xlsr-53-head-v1",
    )
    session.add(prediction)
    session.commit()
    session.refresh(prediction)

    assert prediction.id is not None
    assert prediction.status == TaskStatus.NEW
    assert prediction.threshold_used == 0.37
    assert prediction.model_version == "xlsr-53-head-v1"


def test_prediction_to_queue_message(session):
    user = User(email="q@test.ru", username="q", password="h")
    session.add(user)
    session.commit()
    session.refresh(user)

    prediction = Prediction(
        audio_filename="/test/q.wav", user_id=user.id, status=TaskStatus.QUEUED
    )
    session.add(prediction)
    session.commit()
    session.refresh(prediction)

    msg = prediction.to_queue_message()
    assert msg["task_id"] == prediction.id
    assert msg["audio_filename"] == "/test/q.wav"


def test_task_status_enum():
    assert TaskStatus.NEW.value == "new"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
