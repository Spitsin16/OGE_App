from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.exceptions.exception_classes import EmailAlreadyRegisteredError
from backend.app.models.auth_session import AuthSession
from backend.app.models.user import User
from backend.utils.passwords import hash_password
from backend.utils.tokens import (
    calculate_refresh_token_expires_at,
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, email: str, password: str) -> tuple[User, str, str]:
        normalized_email = email.strip().lower()

        existing_user = await self.db.scalar(
            select(User).where(User.email == normalized_email)
        )

        if existing_user is not None:
            raise EmailAlreadyRegisteredError("Email already registered")

        hashed_password = await hash_password(password)

        user = User(email=normalized_email, password_hash=hashed_password)

        self.db.add(user)

        try:
            await self.db.flush()
            refresh_token = create_refresh_token()

            auth_session = AuthSession(
                user_id=user.id,
                refresh_token_hash=hash_refresh_token(refresh_token),
                expires_at=calculate_refresh_token_expires_at(),
            )
            self.db.add(auth_session)

            access_token = create_access_token(user.id)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise EmailAlreadyRegisteredError("Email already registered")

        return user, access_token, refresh_token
