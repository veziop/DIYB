"""
filename: conftest.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Configuration of the PyTest suite.
"""

from fastapi.testclient import TestClient
from pytest import fixture
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base, get_db
from api.main import app

client = TestClient(app)

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Fixture to create the database schema before any tests run
@fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# Fixture to override the `get_db` dependency
@fixture()
def db_session():
    # Create a new database session for a test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override FastAPI's dependency to use the test database session
@fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client
