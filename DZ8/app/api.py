"""SafeCall Voice Guard — FastAPI Application Entry Point."""
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database.config import get_settings
from database.initdb import init_db
from routes.home import home_route
from routes.auth import auth_route
from routes.predict import predict_route
from auth.authenticate import RequiresLogin


def create_application() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.API_VERSION,
    )
    application.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
    application.include_router(home_route, tags=["Home"])
    application.include_router(auth_route, prefix="/auth", tags=["Auth"])
    application.include_router(predict_route, prefix="/api/predict", tags=["Predict"])

    @application.exception_handler(RequiresLogin)
    async def requires_login_handler(request: Request, exc: RequiresLogin):
        return RedirectResponse(url="/auth/login", status_code=302)

    return application


app = create_application()


@app.on_event("startup")
async def on_startup():
    init_db(drop_all=False)


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=False)
