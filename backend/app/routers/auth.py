from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from backend.app.service.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=AuthResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)

    user, access_token, refresh_token = await service.register(
        data.email, data.password
    )
    return AuthResponse(
        user=user, access_token=access_token, refresh_token=refresh_token
    )


@router.post("/login", status_code=200, response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)

    user, access_token, refresh_token = await service.login(data.email, data.password)

    return AuthResponse(
        user=user, access_token=access_token, refresh_token=refresh_token
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)

    access_token, refresh_token = await service.refresh_tokens(data.refresh_token)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
