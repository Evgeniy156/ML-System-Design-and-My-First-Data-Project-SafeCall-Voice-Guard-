"""Auth routes — login, token, register, logout."""
from fastapi import APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from database.config import get_settings
from database.database import get_session
from models.user import User, UserCreate
from services.auth.loginform import LoginForm
from services.crud.user import get_user_by_email, create_user

auth_route = APIRouter()
templates = Jinja2Templates(directory="view")
hash_password = HashPassword()
settings = get_settings()


@auth_route.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@auth_route.post("/token")
async def login(request: Request, session: Session = Depends(get_session)):
    form = LoginForm(request)
    await form.load_data()

    user = get_user_by_email(form.username, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not hash_password.verify_hash(form.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token = create_access_token(user.email)
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
    )
    return response


@auth_route.post("/register")
async def register(user_data: UserCreate, session: Session = Depends(get_session)):
    existing = get_user_by_email(user_data.email, session)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=user_data.email,
        username=user_data.username,
        password=hash_password.create_hash(user_data.password),
    )
    created = create_user(user, session)
    return {"message": "User registered", "user_id": created.id}


@auth_route.get("/logout")
async def logout(response: Response):
    redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    redirect.delete_cookie(settings.COOKIE_NAME)
    return redirect
