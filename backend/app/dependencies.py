import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.exceptions.exception_classes import (
    InactiveUserError,
    InvalidAccessTokenError,
)
from backend.app.models import User
from backend.app.utils.tokens import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    auth_data: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):

    if auth_data is None:
        raise InvalidAccessTokenError("Access token is required")

    token = auth_data.credentials
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "access":
            raise InvalidAccessTokenError("Invalid or expired access token")
        user_id = int(payload["sub"])
    except jwt.InvalidTokenError:
        raise InvalidAccessTokenError("Invalid or expired token")

    user = await db.get(User, user_id)

    if user is None:
        raise InvalidAccessTokenError("Invalid or expired access token")

    if not user.is_active:
        raise InactiveUserError("User account is inactive")

    return user
