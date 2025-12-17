"""
회원가입 기능 테스트

테스트 범위:
- POST /auth/api/register 성공/실패 케이스
"""

import os
import sys
import uuid
from datetime import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.models import User, UserSetting


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = f"sqlite:///:memory:?cache=shared&uri=true&mode=memory&unique={uuid.uuid4().hex}"

    with app.app_context():
        db.drop_all()
        db.create_all()

        unique_id = uuid.uuid4().hex[:8]
        existing = User(
            username=f"existing{unique_id}",
            email=f"existing{unique_id}@example.com",
            is_active=True,
            is_admin=False,
        )
        existing.set_password("password123")
        db.session.add(existing)
        db.session.flush()

        existing_setting = UserSetting(
            user_id=existing.id,
            language="ko",
            notification_time=time(9, 0),
            is_notification_enabled=True,
        )
        db.session.add(existing_setting)
        db.session.commit()

        app.existing_username = existing.username
        app.existing_email = existing.email

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


class TestRegisterAPI:
    def test_register_success(self, app, client):
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "username": f"newuser{unique_id}",
            "email": f"new{unique_id}@example.com",
            "password": "password123",
        }

        response = client.post("/auth/api/register", json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["user"]["username"] == payload["username"]
        assert data["user"]["email"] == payload["email"]

        with app.app_context():
            created = User.query.filter_by(username=payload["username"]).first()
            assert created is not None
            setting = UserSetting.query.filter_by(user_id=created.id).first()
            assert setting is not None

    def test_register_duplicate_username(self, app, client):
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "username": app.existing_username,
            "email": f"other{unique_id}@example.com",
            "password": "password123",
        }
        response = client.post("/auth/api/register", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_register_duplicate_email(self, app, client):
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "username": f"other{unique_id}",
            "email": app.existing_email,
            "password": "password123",
        }
        response = client.post("/auth/api/register", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_register_invalid_email(self, client):
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "username": f"newuser{unique_id}",
            "email": "invalid-email",
            "password": "password123",
        }
        response = client.post("/auth/api/register", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_register_short_password(self, client):
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "username": f"newuser{unique_id}",
            "email": f"new{unique_id}@example.com",
            "password": "short",
        }
        response = client.post("/auth/api/register", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
