#!/usr/bin/env python3
"""
JD模块单元测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.schemas.interview import JDRequest, InterviewReport, JDMetaData, InterviewQuestion


@pytest.fixture
def mock_jd_text():
    """模拟的JD文本"""
    return """
职位：Python后端开发工程师
职责：
1. 负责后端服务的设计、开发和维护
2. 使用Python、FastAPI、SQLAlchemy等技术
3. 与前端团队协作，实现API接口
4. 优化系统性能和安全性
要求：
1. 本科及以上学历，计算机相关专业
2. 3年以上Python开发经验
3. 熟悉FastAPI、Django等Web框架
4. 掌握SQL和NoSQL数据库
5. 具有良好的团队合作精神
"""


@pytest.fixture
def mock_jd_metadata():
    """模拟的JD解析元数据"""
    return JDMetaData(
        tech_stack=["Python", "FastAPI", "SQLAlchemy", "SQL", "NoSQL"],
        years_required="3年以上",
        core_responsibility="负责后端服务的设计、开发和维护",
        soft_skills=["团队合作", "问题解决"],
        company_name="测试公司"
    )


@pytest.fixture
def mock_interview_report(mock_jd_metadata):
    """模拟的面试报告"""
    tech_questions = [
        InterviewQuestion(
            category="基础",
            question="Python中的GIL是什么？如何影响多线程编程？",
            reference_answer="GIL是全局解释器锁，它限制了同一时间只能有一个线程执行Python字节码。在CPU密集型任务中，多线程可能无法充分利用多核CPU。"
        )
    ]
    
    hr_questions = [
        InterviewQuestion(
            category="HR",
            question="请介绍一下你之前的Python后端开发经验。",
            reference_answer="我有3年Python后端开发经验，主要使用FastAPI和Django框架，负责过多个Web应用的开发和维护。"
        )
    ]
    
    return InterviewReport(
        session_id=1,
        meta=mock_jd_metadata,
        tech_questions=tech_questions,
        hr_questions=hr_questions,
        system_design_question=None,
        company_analysis="测试公司是一家技术型企业，专注于软件开发。",
        reference_sources=["python_guide.pdf"]
    )


@patch('app.api.routers.jd.generate_interview_guide', new_callable=AsyncMock)
async def test_generate_guide(mock_generate_interview_guide, 
                         client: TestClient, test_token: str, mock_jd_text, mock_interview_report):
    """测试流式生成面试指南"""
    # 配置模拟对象
    mock_generate_interview_guide.return_value = mock_interview_report
    
    # 创建测试请求
    request_data = JDRequest(jd_text=mock_jd_text)
    
    response = client.post(
        "/api/v1/jd/generate-guide",
        json=request_data.dict(),
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # 读取流式响应内容
    content = response.content.decode("utf-8")
    assert "data:" in content
    assert "[DONE]" in content
    
    # 验证模拟函数被调用
    mock_generate_interview_guide.assert_called_once()


@patch('app.api.routers.jd.get_llm')
@patch('app.api.routers.jd.sse_manager')
@patch('app.api.routers.jd.ChatPromptTemplate')
@patch('app.api.routers.jd.StrOutputParser')
async def test_stream_system_design(mock_str_parser, mock_prompt_template, mock_sse_manager, mock_get_llm, client: TestClient, test_token: str):
    """测试流式生成系统设计题答案"""
    # 模拟流式响应内容
    stream_content = ["系统设计方案：\n", "1. 架构设计\n", "2. 数据库选型\n"]
    
    # 模拟链
    class MockChain:
        async def astream(self, input_dict):
            for chunk in stream_content:
                yield chunk
    
    mock_chain = MockChain()
    
    # 模拟StrOutputParser的__or__方法返回链
    mock_parser_instance = MagicMock()
    mock_parser_instance.__or__.return_value = mock_chain
    mock_str_parser.return_value = mock_parser_instance
    
    # 模拟ChatPromptTemplate的__or__方法返回一个可以与parser组合的对象
    mock_prompt_instance = MagicMock()
    mock_prompt_instance.__or__.return_value = mock_parser_instance
    mock_prompt_template.from_template.return_value = mock_prompt_instance
    
    # 模拟get_llm返回一个LLM对象
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    # 模拟sse_manager的add_connection方法
    mock_send_queue = AsyncMock()
    mock_sse_manager.add_connection = AsyncMock(return_value=("test_client_id", mock_send_queue))
    # 模拟remove_connection方法
    mock_sse_manager.remove_connection = AsyncMock()
    
    response = client.post(
        "/api/v1/jd/stream/system-design?tech_stack=Python&topic=用户认证系统",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # 读取流式响应内容
    content = response.content.decode("utf-8")
    assert "data:" in content
    assert "系统设计方案" in content
    assert "[DONE]" in content
    
    # 验证模拟函数被调用
    mock_get_llm.assert_called_once()


@patch('app.api.routers.jd.generate_interview_guide', new_callable=AsyncMock)
async def test_generate_guide_error(mock_generate_interview_guide, client: TestClient, test_token: str, mock_jd_text):
    """测试生成面试指南失败的情况"""
    # 配置模拟对象抛出异常
    mock_generate_interview_guide.side_effect = Exception("生成失败")
    
    # 创建测试请求
    request_data = JDRequest(jd_text=mock_jd_text)
    
    response = client.post(
        "/api/v1/jd/generate-guide",
        json=request_data.dict(),
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    # API捕获了generate_interview_guide抛出的异常并通过SSE返回错误信息，所以应该返回200
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # 读取流式响应内容
    content = response.content.decode("utf-8")
    assert "data:" in content
    assert "error" in content.lower()
    assert "生成失败" in content
    
    # 验证模拟函数被调用
    mock_generate_interview_guide.assert_called_once()


@pytest.mark.parametrize("years_required, expected", [
    ("3年以上", "3年以上"),
    (None, "不限"),
    ("", "")
])
def test_jd_metadata_field_validator(years_required, expected):
    """测试JD元数据的字段验证器"""
    metadata = JDMetaData(
        tech_stack=["Python"],
        years_required=years_required,
        core_responsibility="测试",
        soft_skills=[],
        company_name="测试公司"
    )
    
    assert metadata.years_required == expected
