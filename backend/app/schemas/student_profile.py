from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.student_profile import EnglishLevel


class StudentProfileCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    school_grade: int = Field(ge=1, le=11)
    self_assessed_english_level: EnglishLevel


class StudentProfileUpdate(BaseModel):
    first_name: str | None = Field(min_length=1, max_length=100, default=None)
    last_name: str | None = Field(min_length=1, max_length=100, default=None)
    school_grade: int | None = Field(ge=1, le=11, default=None)
    self_assessed_english_level: EnglishLevel | None = None


class StudentProfileResponse(StudentProfileCreate):
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
