import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.student_profile import EnglishLevel, StudentProfile
from backend.app.models.user import User

pytestmark = pytest.mark.anyio

TEST_PASSWORD = "strong-password"


async def register_user(
    client: AsyncClient,
    email: str = "profile-student@example.com",
) -> dict:
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 201
    return response.json()


def authorization_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def create_profile(
    client: AsyncClient,
    access_token: str,
    **overrides,
):
    payload = {
        "first_name": "Kirill",
        "last_name": "Spitsin",
        "school_grade": 9,
        "self_assessed_english_level": "basic",
    }
    payload.update(overrides)

    return await client.post(
        "/student_profile/create",
        json=payload,
        headers=authorization_headers(access_token),
    )


async def test_create_profile_persists_student_data(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    registration = await register_user(client)

    response = await create_profile(client, registration["access_token"])

    assert response.status_code == 201

    body = response.json()
    assert body["user_id"] == registration["user"]["id"]
    assert body["first_name"] == "Kirill"
    assert body["last_name"] == "Spitsin"
    assert body["school_grade"] == 9
    assert body["self_assessed_english_level"] == "basic"
    assert body["created_at"]
    assert body["updated_at"]

    profile = await db_session.get(StudentProfile, registration["user"]["id"])
    assert profile is not None
    assert profile.first_name == "Kirill"
    assert profile.self_assessed_english_level is EnglishLevel.BASIC


async def test_create_profile_rejects_duplicate(client: AsyncClient) -> None:
    registration = await register_user(client)
    access_token = registration["access_token"]

    first_response = await create_profile(client, access_token)
    second_response = await create_profile(client, access_token)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Student profile already exists",
    }


async def test_get_profile_returns_current_user_profile(
    client: AsyncClient,
) -> None:
    registration = await register_user(client)
    access_token = registration["access_token"]
    await create_profile(client, access_token)

    response = await client.get(
        "/student_profile/me",
        headers=authorization_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == registration["user"]["id"]
    assert response.json()["first_name"] == "Kirill"


async def test_get_profile_returns_not_found_before_onboarding(
    client: AsyncClient,
) -> None:
    registration = await register_user(client)

    response = await client.get(
        "/student_profile/me",
        headers=authorization_headers(registration["access_token"]),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}


async def test_update_profile_changes_only_provided_fields(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    registration = await register_user(client)
    access_token = registration["access_token"]
    await create_profile(client, access_token)

    response = await client.patch(
        "/student_profile/me",
        json={
            "school_grade": 10,
            "self_assessed_english_level": "developing",
        },
        headers=authorization_headers(access_token),
    )

    assert response.status_code == 200

    body = response.json()
    assert body["first_name"] == "Kirill"
    assert body["last_name"] == "Spitsin"
    assert body["school_grade"] == 10
    assert body["self_assessed_english_level"] == "developing"

    profile = await db_session.get(StudentProfile, registration["user"]["id"])
    assert profile is not None
    assert profile.school_grade == 10
    assert profile.self_assessed_english_level is EnglishLevel.DEVELOPING


async def test_update_profile_accepts_empty_payload(client: AsyncClient) -> None:
    registration = await register_user(client)
    access_token = registration["access_token"]
    created_response = await create_profile(client, access_token)

    response = await client.patch(
        "/student_profile/me",
        json={},
        headers=authorization_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json() == created_response.json()


async def test_update_profile_returns_not_found_before_onboarding(
    client: AsyncClient,
) -> None:
    registration = await register_user(client)

    response = await client.patch(
        "/student_profile/me",
        json={"school_grade": 10},
        headers=authorization_headers(registration["access_token"]),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}


@pytest.mark.parametrize(
    "payload",
    [
        {"first_name": ""},
        {"last_name": ""},
        {"school_grade": 12},
        {"self_assessed_english_level": "advanced"},
    ],
)
async def test_create_profile_validates_payload(
    client: AsyncClient,
    payload: dict,
) -> None:
    registration = await register_user(client)

    response = await create_profile(
        client,
        registration["access_token"],
        **payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        (
            "POST",
            "/student_profile/create",
            {
                "first_name": "Kirill",
                "last_name": "Spitsin",
                "school_grade": 9,
                "self_assessed_english_level": "basic",
            },
        ),
        ("GET", "/student_profile/me", None),
        ("PATCH", "/student_profile/me", {"school_grade": 10}),
    ],
)
async def test_profile_endpoints_require_authentication(
    client: AsyncClient,
    method: str,
    path: str,
    payload: dict | None,
) -> None:
    response = await client.request(method, path, json=payload)

    assert response.status_code == 401


async def test_users_can_access_only_their_own_profiles(
    client: AsyncClient,
) -> None:
    first_registration = await register_user(client, "first@example.com")
    second_registration = await register_user(client, "second@example.com")

    await create_profile(
        client,
        first_registration["access_token"],
        first_name="First",
    )
    await create_profile(
        client,
        second_registration["access_token"],
        first_name="Second",
    )

    first_response = await client.get(
        "/student_profile/me",
        headers=authorization_headers(first_registration["access_token"]),
    )
    second_response = await client.get(
        "/student_profile/me",
        headers=authorization_headers(second_registration["access_token"]),
    )

    assert first_response.json()["first_name"] == "First"
    assert second_response.json()["first_name"] == "Second"


async def test_deleting_user_cascades_to_profile(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    registration = await register_user(client)
    user_id = registration["user"]["id"]
    await create_profile(client, registration["access_token"])

    user = await db_session.get(User, user_id)
    assert user is not None

    await db_session.delete(user)
    await db_session.commit()

    profile = await db_session.get(StudentProfile, user_id)
    assert profile is None
