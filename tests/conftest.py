"""Fixtures bersama seluruh suite: klien API dan sesi database uji."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app import models  # noqa: F401  — registrasi model ke Base.metadata


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user(db, role: str, email: str, instansi: str | None = None):
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        nama=f"Pengguna {role}",
        email=email,
        password_hash=hash_password("rahasia123"),
        role=role,
        instansi_daerah=instansi,
    )
    db.add(user)
    db.commit()
    return user


def auth_header(client, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "rahasia123"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def admin_user(db_session):
    return create_user(db_session, "admin", "admin@sigap.id")


@pytest.fixture()
def pimpinan_user(db_session):
    return create_user(db_session, "pimpinan", "pimpinan@sigap.id")


@pytest.fixture()
def bpbd_user(db_session):
    return create_user(db_session, "bpbd", "bpbd@sigap.id", instansi="BPBD Surabaya")


@pytest.fixture()
def admin_headers(client, admin_user):
    return auth_header(client, admin_user.email)
