from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.models.auth_session import AuthSession
from backend.app.models.user import User
from backend.app.utils.passwords import verify_password
from backend.app.utils.tokens import hash_refresh_token

pytestmark = pytest.mark.anyio

TEST_EMAIL = "student@example.com"
TEST_PASSWORD = "strong-password"


async def register_user(
    client: AsyncClient,
    email: str = TEST_EMAIL,
    password: str = TEST_PASSWORD,
):
    return await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )


async def test_register_creates_user_and_session(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    response = await register_user(client, email=" Student@Example.com ")

    assert response.status_code == 201

    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == TEST_EMAIL
    assert "password_hash" not in body["user"]

    user = await db_session.scalar(select(User).where(User.email == TEST_EMAIL))
    assert user is not None
    assert await verify_password(TEST_PASSWORD, user.password_hash)

    auth_session = await db_session.scalar(
        select(AuthSession).where(AuthSession.user_id == user.id)
    )
    assert auth_session is not None
    assert auth_session.refresh_token_hash == hash_refresh_token(body["refresh_token"])
    assert auth_session.refresh_token_hash != body["refresh_token"]


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    first_response = await register_user(client)
    second_response = await register_user(client, email="STUDENT@example.com")

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "Email already registered"}


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("not-an-email", TEST_PASSWORD),
        (TEST_EMAIL, "short"),
    ],
)
async def test_register_validates_payload(
    client: AsyncClient,
    email: str,
    password: str,
) -> None:
    response = await register_user(client, email=email, password=password)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("email", "password"),
    [
        (TEST_EMAIL, "wrong-password"),
        ("missing@example.com", TEST_PASSWORD),
    ],
)
async def test_login_rejects_invalid_credentials(
    client: AsyncClient,
    email: str,
    password: str,
) -> None:
    await register_user(client)

    response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Wrong email or password"}


async def test_login_returns_tokens_and_creates_new_session(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await register_user(client)

    response = await client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == TEST_EMAIL

    session_count = await db_session.scalar(select(func.count(AuthSession.id)))
    assert session_count == 2


async def test_refresh_rotates_token_in_same_session(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    register_response = await register_user(client)
    first_refresh_token = register_response.json()["refresh_token"]
    auth_session = await db_session.scalar(select(AuthSession))
    assert auth_session is not None
    original_expires_at = auth_session.expires_at

    refresh_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": first_refresh_token},
    )

    assert refresh_response.status_code == 200

    second_refresh_token = refresh_response.json()["refresh_token"]
    assert second_refresh_token != first_refresh_token

    session_count = await db_session.scalar(select(func.count(AuthSession.id)))
    assert session_count == 1

    assert auth_session.refresh_token_hash == hash_refresh_token(second_refresh_token)
    assert auth_session.expires_at == original_expires_at

    reused_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": first_refresh_token},
    )
    assert reused_response.status_code == 401


async def test_refresh_rejects_expired_session(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    register_response = await register_user(client)
    refresh_token = register_response.json()["refresh_token"]

    auth_session = await db_session.scalar(select(AuthSession))
    assert auth_session is not None
    auth_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    response = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401


async def test_logout_revokes_refresh_token_and_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    register_response = await register_user(client)
    refresh_token = register_response.json()["refresh_token"]

    logout_response = await client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_response.status_code == 204
    assert logout_response.content == b""

    auth_session = await db_session.scalar(select(AuthSession))
    assert auth_session is not None
    assert auth_session.revoked_at is not None

    refresh_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401

    repeated_logout_response = await client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert repeated_logout_response.status_code == 204


async def test_logout_accepts_unknown_refresh_token(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/logout",
        json={"refresh_token": "unknown-refresh-token"},
    )

    assert response.status_code == 204


async def test_me_returns_current_user(client: AsyncClient) -> None:
    register_response = await register_user(client)
    body = register_response.json()

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == body["user"]["id"]
    assert response.json()["email"] == TEST_EMAIL


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer invalid-token"},
    ],
)
async def test_me_rejects_missing_or_invalid_access_token(
    client: AsyncClient,
    headers: dict[str, str],
) -> None:
    response = await client.get("/auth/me", headers=headers)

    assert response.status_code == 401


async def test_me_rejects_expired_access_token(client: AsyncClient) -> None:
    register_response = await register_user(client)
    user_id = register_response.json()["user"]["id"]
    now = datetime.now(UTC)

    expired_access_token = jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_access_token}"},
    )

    assert response.status_code == 401


async def test_inactive_user_cannot_login_refresh_or_access_me(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    register_response = await register_user(client)
    body = register_response.json()

    user = await db_session.get(User, body["user"]["id"])
    assert user is not None
    user.is_active = False
    await db_session.commit()

    login_response = await client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    refresh_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert login_response.status_code == 403
    assert refresh_response.status_code == 403
    assert me_response.status_code == 403
