import os
import pytest
from collections.abc import Generator
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

os.environ["DROID_HAL"] = "mock"
os.environ["SECRET_KEY"] = "testsecretkeymustbe32bytesminimumlongfortests"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.auth.security import get_password_hash, create_access_token
from app.db.models import User
from app.db.session import get_session
from app.main import app

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@pytest.fixture(name="db_setup", autouse=True, scope="function")
def db_setup_fixture() -> Generator[None, None, None]:
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        admin_user = User(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True
        )
        operator_user = User(
            username="operator",
            hashed_password=get_password_hash("operator123"),
            role="operator",
            is_active=True
        )
        session.add(admin_user)
        session.add(operator_user)
        session.commit()
    yield
    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(name="client", scope="session")
def client_fixture() -> Generator[TestClient, None, None]:
    def get_session_override() -> Generator[Session, None, None]:
        with Session(test_engine) as sess:
            yield sess

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="admin_token")
def admin_token_fixture() -> str:
    return create_access_token(data={"sub": "admin", "role": "admin"})

@pytest.fixture(name="operator_token")
def operator_token_fixture() -> str:
    return create_access_token(data={"sub": "operator", "role": "operator"})
