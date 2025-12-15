#!/usr/bin/env python3
"""
Chat模块单元测试
"""

import pytest
import json
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.core.models import User, ChatSession, ChatMessage


def test_get_sessions(client: TestClient, test_user: User, test_session: ChatSession, test_token: str):
    """测试获取用户的聊天会话列表"""
    response = client.get(
        "/api/v1/chat/history/sessions",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    sessions = response.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 1
    
    # 检查返回的会话是否属于测试用户
    assert sessions[0]["user_id"] == test_user.id
    assert sessions[0]["title"] == "测试会话"


def test_get_sessions_unauthorized(client: TestClient):
    """测试未授权访问获取会话列表"""
    response = client.get("/api/v1/chat/history/sessions")
    
    assert response.status_code == 401


def test_get_messages(client: TestClient, test_user: User, test_session: ChatSession, test_token: str, session: Session):
    """测试获取特定会话的消息历史"""
    # 添加测试消息
    user_msg = ChatMessage(session_id=test_session.id, role="user", content="Hello")
    ai_msg = ChatMessage(session_id=test_session.id, role="assistant", content="Hi there!")
    session.add_all([user_msg, ai_msg])
    session.commit()
    
    response = client.get(
        f"/api/v1/chat/history/messages/{test_session.id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    messages = response.json()
    assert isinstance(messages, list)
    assert len(messages) >= 2
    
    # 检查返回的消息是否属于正确的会话
    assert messages[0]["session_id"] == test_session.id
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["session_id"] == test_session.id
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hi there!"


def test_get_messages_unauthorized(client: TestClient, test_session: ChatSession):
    """测试未授权访问获取消息历史"""
    response = client.get(f"/api/v1/chat/history/messages/{test_session.id}")
    
    assert response.status_code == 401


def test_get_messages_nonexistent_session(client: TestClient, test_user: User, test_token: str):
    """测试获取不存在的会话消息"""
    response = client.get(
        "/api/v1/chat/history/messages/9999",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["status"] == "error"


def test_stream_chat(client: TestClient, test_user: User, test_session: ChatSession, test_token: str):
    """测试流式聊天接口"""
    response = client.post(
        "/api/v1/chat/stream",
        json={"session_id": test_session.id, "content": "Hello"},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # 读取响应内容
    content = response.content.decode("utf-8")
    
    # 检查流数据格式
    assert "data: " in content
    assert "[DONE]" in content
    
    # 检查是否有正常的JSON消息
    lines = content.split("\n")
    json_lines = [line for line in lines if line.startswith("data: {") and not line.startswith("data: [DONE]")]
    
    for json_line in json_lines:
        # 去掉"data: "前缀
        json_str = json_line[6:]
        try:
            data = json.loads(json_str)
            # 检查JSON结构
            assert "type" in data
            assert "content" in data
        except json.JSONDecodeError:
            pass  # 允许非JSON的data行
