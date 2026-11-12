from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.exceptions.exception_classes import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from backend.app.models.auth_session import AuthSession
from backend.app.models.user import User
from backend.app.utils.passwords import hash_password, verify_password
from backend.app.utils.tokens import (
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

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        normalized_email = email.strip().lower()

        existing_user = await self.db.scalar(
            select(User).where(User.email == normalized_email)
        )

        if existing_user is None:
            raise InvalidCredentialsError("Wrong email or password")

        password_is_valid = await verify_password(password, existing_user.password_hash)

        if not password_is_valid:
            raise InvalidCredentialsError("Wrong email or password")

        if not existing_user.is_active:
            raise InactiveUserError("User account is inactive")

        refresh_token = create_refresh_token()

        auth_session = AuthSession(
            user_id=existing_user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            expires_at=calculate_refresh_token_expires_at(),
        )

        self.db.add(auth_session)

        access_token = create_access_token(existing_user.id)

        await self.db.commit()

        return existing_user, access_token, refresh_token

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        refresh_token_hash = hash_refresh_token(refresh_token)

        auth_session = await self.db.scalar(
            select(AuthSession)
            .where(AuthSession.refresh_token_hash == refresh_token_hash)
            .with_for_update()
        )

        now = datetime.now(UTC)

        if (
            (auth_session is None)
            or (auth_session.expires_at <= now)
            or (auth_session.revoked_at is not None)
        ):
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        user = await self.db.get(User, auth_session.user_id)

        if user is None:
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        if not user.is_active:
            raise InactiveUserError("User account is inactive")

        new_refresh_token = create_refresh_token()

        auth_session.refresh_token_hash = hash_refresh_token(new_refresh_token)

        new_access_token = create_access_token(user.id)

        await self.db.commit()

        return new_access_token, new_refresh_token

    async def logout(self, refresh_token: str) -> None:
        refresh_token_hash = hash_refresh_token(refresh_token)

        auth_session = await self.db.scalar(
            select(AuthSession)
            .where(AuthSession.refresh_token_hash == refresh_token_hash)
            .with_for_update()
        )

        now = datetime.now(UTC)

        if (
            (auth_session is None)
            or (auth_session.expires_at <= now)
            or (auth_session.revoked_at is not None)
        ):
            return

        auth_session.revoked_at = now

        await self.db.commit()
