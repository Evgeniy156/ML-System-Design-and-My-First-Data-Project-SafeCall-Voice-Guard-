"""Prediction routes — send_task, send_task_result, tasks, upload UI.

Pattern from example/app/routes/ml.py — adapted for SafeCall audio upload.
"""
import os
import shutil
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from auth.authenticate import authenticate, authenticate_cookie
from database.database import get_session
from models.prediction import Prediction, TaskStatus, PredictionCreate
from services.rm.rm import safecall_rmq_client
from services.crud.prediction import PredictionService

logger = logging.getLogger(__name__)
predict_route = APIRouter()
templates = Jinja2Templates(directory="view")

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_service(session: Session = Depends(get_session)) -> PredictionService:
    return PredictionService(session)


# ─── API endpoints ────────────────────────────────────────────
@predict_route.post("/send_task")
async def send_task(
    file: UploadFile = File(...),
    user: str = Depends(authenticate),
    service: PredictionService = Depends(get_service),
    session: Session = Depends(get_session),
):
    """Upload audio and create async prediction task."""
    from services.crud.user import get_user_by_email

    db_user = get_user_by_email(user, session)
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    # Save uploaded file with a safe basename.
    raw_filename = (file.filename or "audio.wav").replace("\\", "/")
    filename = f"{db_user.id}_{os.path.basename(raw_filename)}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    created = None
    try:
        task = PredictionCreate(
            audio_filename=filepath, user_id=db_user.id, status=TaskStatus.NEW
        )
        created = service.create(task)
        sent = safecall_rmq_client.send_task(created)
        if not sent:
            service.set_failed(created.id, "RabbitMQ producer failed to publish task")
            raise HTTPException(
                status_code=503,
                detail="Task was saved, but RabbitMQ is unavailable.",
            )
        service.set_status(created.id, TaskStatus.QUEUED)
        return {"message": "Task sent successfully!", "task_id": created.id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"send_task error: {e}")
        if created:
            service.set_status(created.id, TaskStatus.FAILED)
        raise HTTPException(status_code=500, detail=str(e))


@predict_route.post("/send_task_failure")
def send_task_failure(
    task_id: int,
    error: str,
    service: PredictionService = Depends(get_service),
):
    """Callback from ML worker when task processing fails permanently."""
    service.set_failed(task_id, error)
    return {"message": "Task marked as failed"}


@predict_route.post("/send_task_result")
def send_task_result(
    task_id: int,
    result: str,
    service: PredictionService = Depends(get_service),
):
    """Callback from ML worker — receives prediction result."""
    try:
        service.set_result(task_id, result)
        return {"message": "Task result saved successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@predict_route.get("/tasks")
async def get_all_tasks(
    user: str = Depends(authenticate),
    service: PredictionService = Depends(get_service),
):
    return service.get_all()


@predict_route.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    user: str = Depends(authenticate),
    service: PredictionService = Depends(get_service),
):
    task = service.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ─── UI pages ─────────────────────────────────────────────────
@predict_route.get("/upload")
async def upload_page(request: Request, user: str = Depends(authenticate_cookie)):
    return templates.TemplateResponse(request, "upload.html", {"user": user})


@predict_route.get("/history")
async def history_page(
    request: Request,
    user: str = Depends(authenticate_cookie),
    service: PredictionService = Depends(get_service),
    session: Session = Depends(get_session),
):
    from services.crud.user import get_user_by_email

    db_user = get_user_by_email(user, session)
    predictions = service.get_by_user(db_user.id) if db_user else []
    return templates.TemplateResponse(
        request,
        "history.html",
        {"user": user, "predictions": predictions},
    )
