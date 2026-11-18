from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.exceptions.exception_classes import (
    ProfileAlreadyExistsError,
)
from backend.app.models.student_profile import StudentProfile
from backend.app.schemas.student_profile import StudentProfileCreate


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
