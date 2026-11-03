from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.database import get_session
from app.core.rate_limit import ALL_LIMITERS
from app.main import app
from app.models import Match, Message, Participant, Rating, Report, User  # noqa: F401


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> Generator[None, None, None]:
    """Os limitadores guardam estado no processo: sem isso, um teste herdaria as tentativas do
    anterior (todas vêm do mesmo IP do TestClient)."""
    for limiter in ALL_LIMITERS:
        limiter.reset()
    yield


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def get_session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
