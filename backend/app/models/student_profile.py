from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class EnglishLevel(StrEnum):
    STARTING = "starting"
    BASIC = "basic"
    DEVELOPING = "developing"
    CONFIDENT = "confident"
    UNSURE = "unsure"


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    __table_args__ = (
        CheckConstraint(
            "school_grade BETWEEN 1 AND 11",
            name="ck_student_profiles_school_grade",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)

    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    school_grade: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    self_assessed_english_level: Mapped[EnglishLevel] = mapped_column(
        Enum(EnglishLevel, name="english_level_enum"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
