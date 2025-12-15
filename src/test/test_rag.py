#!/usr/bin/env python3
"""
RAG模块单元测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.chains.rag_chain import ask_knowledge_base
from app.core.models import RAGRequest


@pytest.fixture
def mock_rag_question():
    """模拟的RAG查询问题"""
    return "什么是RAG技术？"


@pytest.fixture
def mock_rag_answer():
    """模拟的RAG回答结果"""
    return {
        "answer": "RAG是检索增强生成的缩写，是一种将外部知识库与生成模型相结合的技术。",
        "sources": ["rag_article.pdf", "tech_blog.txt"],
        "original_query": "什么是RAG技术？",
        "rewritten_query": "什么是检索增强生成（RAG）技术及其工作原理？"
    }


@patch('app.api.routers.rag.ask_knowledge_base', new_callable=AsyncMock)
async def test_query_knowledge_base_normal(mock_ask_knowledge_base, client: TestClient, test_token: str, mock_rag_question, mock_rag_answer):
    """测试正常查询知识库"""
    # 配置模拟对象为AsyncMock
    mock_ask_knowledge_base.return_value = mock_rag_answer
    
    # 创建测试请求
    request_data = RAGRequest(question=mock_rag_question)
    
    response = client.post(
        "/api/v1/qa/qa",
        json=request_data.dict(),
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    
    result = response.json()
    assert "answer" in result
    assert "sources" in result
    assert result["answer"] == mock_rag_answer["answer"]
    assert result["sources"] == mock_rag_answer["sources"]
    assert "error" not in result


@patch('app.api.routers.rag.ask_knowledge_base', new_callable=AsyncMock)
async def test_query_knowledge_base_empty_question(mock_ask_knowledge_base, client: TestClient, test_token: str):
    """测试空查询问题"""
    # 创建空查询请求
    request_data = RAGRequest(question="")
    
    response = client.post(
        "/api/v1/qa/qa",
        json=request_data.dict(),
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    
    result = response.json()
    assert "answer" in result
    assert "sources" in result
    assert isinstance(result["answer"], str)
    assert isinstance(result["sources"], list)


@patch('app.api.routers.rag.ask_knowledge_base', new_callable=AsyncMock)
async def test_query_knowledge_base_value_error(mock_ask_knowledge_base, client: TestClient, test_token: str, mock_rag_question):
    """测试查询时发生ValueError错误"""
    # 配置模拟对象抛出ValueError
    mock_ask_knowledge_base.side_effect = ValueError("知识库未构建")
    
    # 创建测试请求
    request_data = RAGRequest(question=mock_rag_question)
    
    response = client.post(
        "/api/v1/qa/qa",
        json=request_data.dict(),
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    
    result = response.json()
    assert "answer" in result
    assert "sources" in result
    assert "查询失败" in result["answer"]
    assert result["sources"] == []


@patch('app.api.routers.rag.ask_knowledge_base', new_callable=AsyncMock)
async def test_query_knowledge_base_exception(mock_ask_knowledge_base, client: TestClient, test_token: str, mock_rag_question):
    """测试查询时发生其他异常"""
    # 配置模拟对象抛出Exception
    mock_ask_knowledge_base.side_effect = Exception("数据库连接失败")
    
    # 创建测试请求
    request_data = RAGRequest(question=mock_rag_question)
    
    response = client.post(
        "/api/v1/qa/qa",
        json=request_data.dict(),
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 500
    
    result = response.json()
    assert "code" in result
    assert "message" in result
    assert "查询知识库失败" in result["message"]


@patch('app.api.routers.rag.ask_knowledge_base', new_callable=AsyncMock)
async def test_query_knowledge_base_no_sources(mock_ask_knowledge_base, client: TestClient, test_token: str, mock_rag_question):
    """测试没有来源的查询结果"""
    # 配置模拟对象返回没有来源的结果
    mock_answer = {
        "answer": "这是一个没有来源的回答。",
        "sources": [],
        "original_query": mock_rag_question,
        "rewritten_query": mock_rag_question
    }
    mock_ask_knowledge_base.return_value = mock_answer
    
    # 创建测试请求
    request_data = RAGRequest(question=mock_rag_question)
    
    response = client.post(
        "/api/v1/qa/qa",
        json=request_data.dict(),
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    
    result = response.json()
    assert "answer" in result
    assert "sources" in result
    assert result["answer"] == mock_answer["answer"]
    assert result["sources"] == []
