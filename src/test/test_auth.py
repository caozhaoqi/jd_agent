#!/usr/bin/env python3
"""
Auth模块单元测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.core.models import User
from app.api.routers.auth import get_password_hash


def test_register(client: TestClient):
    """测试用户注册接口"""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "new_user", "password": "new_password"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "message" in response.json()
    assert response.json()["message"] == "注册成功"


def test_register_existing_user(client: TestClient, test_user: User):
    """测试注册已存在的用户"""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "test_user", "password": "new_password"}
    )
    
    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_login(client: TestClient, test_user: User):
    """测试用户登录接口"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_user", "password": "test_password"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "data" in response.json()
    assert "access_token" in response.json()["data"]


def test_login_invalid_password(client: TestClient, test_user: User):
    """测试使用错误密码登录"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_user", "password": "wrong_password"}
    )
    
    assert response.status_code == 401
    assert response.json()["status"] == "error"


def test_login_nonexistent_user(client: TestClient):
    """测试登录不存在的用户"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistent_user", "password": "password"}
    )
    
    assert response.status_code == 401
    assert response.json()["status"] == "error"



