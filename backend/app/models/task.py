from backend.app.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Text, ForeignKey, SmallInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY

class Task(Base):

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    exam_part: Mapped[str] = mapped_column(String(20))
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    fipi_group_id: Mapped[str | None] = mapped_column(String(6), nullable = True) 

class TaskMaterial(Base):

    __tablename__ = "task_materials"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tasks.id"))
    material_type: Mapped[str] = mapped_column(String(20))
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)

class TaskItem(Base):

    __tablename__ = "tasks_items"

    __table_args__ = (UniqueConstraint("task_id", "position"),)


    id: Mapped[int] = mapped_column(BigInteger,primary_key=True)
    task_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("tasks.id"))
    exam_number: Mapped[int] = mapped_column(SmallInteger)
    position: Mapped[int] = mapped_column(SmallInteger)
    prompt: Mapped[str | None] = mapped_column(Text)
    correct_answers: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    fipi_question_id: Mapped[str | None] = mapped_column(String(6))

class TaskOption(Base):
    __tablename__ = "task_options"

    id: Mapped[int] = mapped_column(BigInteger,primary_key=True)

    task_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("tasks.id"))

    task_item_id: Mapped[int | None] = mapped_column(BigInteger,ForeignKey("tasks_items.id"))

    position: Mapped[int] = mapped_column(SmallInteger)

    text: Mapped[str] = mapped_column(Text)