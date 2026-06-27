"""Password hashing with passlib + bcrypt."""
from passlib.context import CryptContext


class HashPassword:
    def __init__(self):
        self.context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_hash(self, password: str) -> str:
        return self.context.hash(password)

    def verify_hash(self, plain: str, hashed: str) -> bool:
        return self.context.verify(plain, hashed)
