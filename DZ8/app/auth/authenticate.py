"""Authentication dependency — Cookie + Bearer dual scheme from example."""
from fastapi import Depends, HTTPException, status, Request
from auth.jwt_handler import verify_access_token
from services.auth.cookieauth import OAuth2PasswordBearerWithCookie
from database.config import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/auth/token")


class RequiresLogin(Exception):
    """Raised when a UI page requires authentication — triggers redirect to login."""
    pass


async def authenticate(request: Request, token: str = Depends(oauth2_scheme)) -> str:
    """Verify JWT token from cookie or Authorization header."""
    if not token:
        # Try cookie
        token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )
    data = verify_access_token(token)
    return data["user"]


async def authenticate_cookie(request: Request) -> str:
    """Cookie-only authentication for template pages."""
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise RequiresLogin()
    try:
        data = verify_access_token(token)
    except HTTPException:
        raise RequiresLogin()
    return data["user"]
