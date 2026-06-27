"""Login form parser — from example/app/services/auth/loginform.py."""
from fastapi import Request


class LoginForm:
    def __init__(self, request: Request):
        self.request = request
        self.username: str = ""
        self.password: str = ""

    async def load_data(self):
        form = await self.request.form()
        self.username = form.get("username", "")
        self.password = form.get("password", "")
