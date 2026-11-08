from sqlalchemy import URL
from backend.app.config import settings
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine,async_sessionmaker
from collections.abc import AsyncGenerator

database_url = URL.create(drivername="postgresql+asyncpg",
                          username=settings.postgres_user,
                          password=settings.postgres_password.get_secret_value(),
                          host=settings.postgres_host,
                          port=settings.postgres_port,
                          database=settings.postgres_db)

engine = create_async_engine(database_url,
                             pool_pre_ping=True)

SessionLocal = async_sessionmaker(bind=engine,
                            autoflush=False,
                            expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()