"""Uji login dan guard role: hanya pemegang role yang tepat yang lolos."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.router import api_router
from app.core.deps import require_role
from app.core.security import hash_password
from app.models.user import User


def _seed_user(db, role: str, email: str) -> User:
    user = User(
        nama=f"Uji {role}",
        email=email,
        password_hash=hash_password("rahasia123"),
        role=role,
        instansi_daerah="BPBD Surabaya" if role == "bpbd" else None,
    )
    db.add(user)
    db.commit()
    return user


def _guarded_app() -> FastAPI:
    guarded = FastAPI()
    guarded.include_router(api_router)

    @guarded.get("/only-admin", dependencies=[Depends(require_role("admin"))])
    def only_admin() -> dict:
        return {"ok": True}

    return guarded


def test_login_success_returns_token_and_role(client, db_session):
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@sigap.id", "password": "rahasia123"}
    )
    assert response.status_code == 401  # belum ada user — memastikan guard bekerja

    _seed_user(db_session, "admin", "admin@sigap.id")

    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@sigap.id", "password": "rahasia123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "admin"
    assert body["access_token"]


def test_login_wrong_password_401(db_session):
    _seed_user(db_session, "admin", "admin@sigap.id")
    app = _guarded_app()

    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@sigap.id", "password": "salah"}
    )
    assert response.status_code == 401


def test_admin_only_endpoint_blocks_other_roles(db_session):
    _seed_user(db_session, "bpbd", "bpbd@sigap.id")
    _seed_user(db_session, "admin", "admin@sigap.id")
    app = _guarded_app()

    from app.core.database import get_db

    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    client = TestClient(app)

    assert client.get("/only-admin").status_code == 401

    bpbd_token = client.post(
        "/api/v1/auth/login", json={"email": "bpbd@sigap.id", "password": "rahasia123"}
    ).json()["access_token"]
    assert client.get(
        "/only-admin", headers={"Authorization": f"Bearer {bpbd_token}"}
    ).status_code == 403

    admin_token = client.post(
        "/api/v1/auth/login", json={"email": "admin@sigap.id", "password": "rahasia123"}
    ).json()["access_token"]
    assert client.get(
        "/only-admin", headers={"Authorization": f"Bearer {admin_token}"}
    ).status_code == 200
