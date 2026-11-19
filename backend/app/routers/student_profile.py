from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.schemas.student_profile import (
    StudentProfileCreate,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from backend.app.service.student_profile import StudentProfileService

router = APIRouter(prefix="/student_profile", tags=["student_profile"])


@router.post("/create", status_code=201, response_model=StudentProfileResponse)
async def create_student_profile(
    data: StudentProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = StudentProfileService(db)

    return await service.create_profile(current_user.id, data)


@router.get("/me", response_model=StudentProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    service = StudentProfileService(db)

    return await service.get_profile(current_user.id)


@router.patch("/me", response_model=StudentProfileResponse)
async def edit_profile_data(
    data: StudentProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = StudentProfileService(db)

    return await service.update_student_profile(current_user.id, data)
