#!/usr/bin/env python3
"""
测试配置文件：包含所有API测试的通用工具和fixtures
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.core.db_auth import get_session, get_password_hash
from app.core.models import User, ChatSession

# 创建一个内存数据库用于测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    """创建一个数据库会话用于测试"""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """创建一个测试客户端，替换依赖项中的数据库会话"""

    def override_get_session():
        return session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """创建一个测试用户"""
    hashed_password = get_password_hash("test_password")
    user = User(username="test_user", hashed_password=hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="test_session")
def test_session_fixture(session: Session, test_user: User):
    """创建一个测试会话"""
    chat_session = ChatSession(title="测试会话", user_id=test_user.id)
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


@pytest.fixture(name="test_token")
def test_token_fixture(test_user: User, client: TestClient):
    """获取测试用户的访问令牌"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_user", "password": "test_password"},
    )
    data = response.json()
    return data["data"]["access_token"]


@pytest.fixture(scope="session")
def event_loop():
    """为测试提供事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# 通用测试工具函数
def assert_success_response(response, expected_status_code=200):
    """断言响应成功"""
    assert response.status_code == expected_status_code
    assert "status" in response.json()
    assert response.json()["status"] == "success"


def assert_error_response(response, expected_status_code, expected_code=None):
    """断言响应失败"""
    assert response.status_code == expected_status_code
    assert "code" in response.json()
    if expected_code:
        assert response.json()["code"] == expected_code
