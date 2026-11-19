from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.exceptions.exception_classes import (
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
)
from backend.app.models.student_profile import StudentProfile
from backend.app.schemas.student_profile import (
    StudentProfileCreate,
    StudentProfileUpdate,
)


class StudentProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_profile(self, user_id: int, data: StudentProfileCreate):

        existing_profile = await self.db.get(StudentProfile, user_id)

        if existing_profile is not None:
            raise ProfileAlreadyExistsError("Student profile already exists")

        profile = StudentProfile(
            user_id=user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            school_grade=data.school_grade,
            self_assessed_english_level=data.self_assessed_english_level,
        )

        self.db.add(profile)

        try:
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            raise ProfileAlreadyExistsError("Student profile already exists") from error

        await self.db.refresh(profile)

        return profile

    async def get_profile(self, user_id: int):

        profile = await self.db.get(StudentProfile, user_id)

        if profile is None:
            raise ProfileNotFoundError("Profile not found")

        return profile

    async def update_student_profile(self, user_id: int, data: StudentProfileUpdate):

        existing_profile = await self.get_profile(user_id)

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)

        if not update_data:
            return existing_profile

        for field, value in update_data.items():
            setattr(existing_profile, field, value)

        await self.db.commit()
        await self.db.refresh(existing_profile)

        return existing_profile
