"""
Pytest configuration and fixtures.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.db.session import Base, get_db
from app.main import app

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database for each test.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session):
    """
    Create a test client with database override.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_client_data():
    """Sample client data for testing."""
    return {
        "name": "Test Client",
        "description": "A test client for integration testing",
        "external_api_url": "https://jsonplaceholder.typicode.com",
        "external_api_timeout": 30,
        "is_active": True,
        "credentials": {"api_key": "test_key_123", "api_secret": "test_secret_456"},
    }


@pytest.fixture
def sample_integration_sync():
    """Sample integration sync data for testing."""
    return {"endpoint": "/posts", "method": "GET", "params": {"userId": 1}}
