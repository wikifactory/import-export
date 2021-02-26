from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy_utils import create_database, database_exists

from app.db.base_class import Base
from app.db.init_db import init_db
from app.db.session import SessionLocal, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_db() -> None:
    session = SessionLocal()
    if not database_exists(engine.url):
        create_database(engine.url)
    else:
        Base.metadata.drop_all(engine)
    init_db(session)
    session.close()


@pytest.fixture(scope="session")
def db() -> Generator:
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def client() -> Generator:
    with TestClient(app) as c:
        yield c
