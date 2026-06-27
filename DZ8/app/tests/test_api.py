"""API endpoint tests."""


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "safecall-api"


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "SafeCall" in response.text


def test_get_tasks_empty(client):
    response = client.get("/api/predict/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_get_task_not_found(client):
    response = client.get("/api/predict/tasks/999")
    assert response.status_code == 404


def test_send_task_result(client, session):
    """Test worker callback — create prediction, then set result."""
    from models.prediction import Prediction, TaskStatus

    prediction = Prediction(
        audio_filename="/test/audio.wav",
        user_id=1,
        status=TaskStatus.QUEUED,
    )
    session.add(prediction)
    session.commit()
    session.refresh(prediction)

    result = (
        '{"verdict": "SPOOF", "spoof_probability": 0.85, '
        '"confidence": 0.85, "threshold": 0.37, '
        '"processing_time_ms": 1781.3, "model_version": "xlsr-53-head-v1"}'
    )
    response = client.post(
        f"/api/predict/send_task_result?task_id={prediction.id}&result={result}"
    )
    assert response.status_code == 200

    # Verify result was saved
    response = client.get(f"/api/predict/tasks/{prediction.id}")
    data = response.json()
    assert data["status"] == "completed"
    assert data["verdict"] == "SPOOF"
    assert data["processing_time_ms"] == 1781.3
    assert data["model_version"] == "xlsr-53-head-v1"


def test_send_task_success(client, session, monkeypatch):
    """Upload creates a queued prediction when RabbitMQ publish succeeds."""
    from models.user import User
    from models.prediction import Prediction, TaskStatus
    from routes import predict as predict_module

    user = User(email="test@safecall.ru", username="tester", password="hashed")
    session.add(user)
    session.commit()

    monkeypatch.setattr(
        predict_module.safecall_rmq_client,
        "send_task",
        lambda task: True,
    )

    response = client.post(
        "/api/predict/send_task",
        files={"file": ("sample.wav", b"fake-audio-bytes", "audio/wav")},
    )

    assert response.status_code == 200
    task_id = response.json()["task_id"]
    prediction = session.get(Prediction, task_id)
    assert prediction.status == TaskStatus.QUEUED
    assert prediction.audio_filename.endswith("sample.wav")


def test_send_task_marks_failed_when_queue_unavailable(client, session, monkeypatch):
    """RabbitMQ failure must not leave a task stuck in queued state."""
    from sqlmodel import select
    from models.user import User
    from models.prediction import Prediction, TaskStatus
    from routes import predict as predict_module

    user = User(email="test@safecall.ru", username="tester", password="hashed")
    session.add(user)
    session.commit()

    monkeypatch.setattr(
        predict_module.safecall_rmq_client,
        "send_task",
        lambda task: False,
    )

    response = client.post(
        "/api/predict/send_task",
        files={"file": ("sample.wav", b"fake-audio-bytes", "audio/wav")},
    )

    assert response.status_code == 503
    prediction = session.exec(select(Prediction)).first()
    assert prediction.status == TaskStatus.FAILED
    assert "RabbitMQ" in prediction.error_message
