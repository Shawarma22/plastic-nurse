from typing import Generator
from sqlmodel import create_engine, Session, SQLModel
from app.config import settings
from app.logger import logger

connect_args = {"check_same_thread": False, "timeout": 20} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    logger.info("Database schema initialized")

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
