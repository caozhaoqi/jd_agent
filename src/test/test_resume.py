#!/usr/bin/env python3
"""
Resume模块单元测试
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import UploadFile
from io import BytesIO
from app.core.models import User, UserProfile


@pytest.fixture
def mock_resume_text():
    """模拟的简历文本"""
    return """
    个人简历

    基本信息
    姓名：张三
    邮箱：zhangsan@example.com
    电话：13800138000

    教育背景
    2010-2014 北京大学 计算机科学与技术 本科

    工作经验
    2014-2017 腾讯科技有限公司 后端开发工程师
    2017-至今 阿里巴巴集团 高级后端开发工程师

    技术栈
    Python、Java、Go、FastAPI、Spring Boot、Docker、Kubernetes、Redis、MySQL

    项目经验
    1. 电商平台后端系统重构
    2. 微服务架构升级
    """


@pytest.fixture
def create_test_file(mock_resume_text):
    """创建测试文件的辅助函数"""

    def _create_test_file(filename="test_resume.txt", content_type="text/plain"):
        return UploadFile(
            filename=filename,
            content_type=content_type,
            file=BytesIO(mock_resume_text.encode("utf-8")),
        )

    return _create_test_file


async def test_upload_resume(
    client: TestClient, test_user: User, test_token: str, mock_resume_text
):
    """测试上传简历接口"""
    # 创建测试文件
    test_file = BytesIO(mock_resume_text.encode("utf-8"))

    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("test_resume.txt", test_file, "text/plain")},
        headers={"Authorization": f"Bearer {test_token}"},
    )

    assert response.status_code == 200

    result = response.json()
    assert "msg" in result
    assert "new_entries" in result

    # 验证返回消息
    assert result["msg"] in ["简历解析成功", "简历解析完成，但未提取到有效信息"]

    # 验证新增条目数
    assert isinstance(result["new_entries"], int)
    assert result["new_entries"] >= 0


def test_upload_resume_unauthorized(client: TestClient, mock_resume_text):
    """测试未授权访问上传简历接口"""
    # 创建测试文件
    test_file = BytesIO(mock_resume_text.encode("utf-8"))

    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("test_resume.txt", test_file, "text/plain")},
    )

    assert response.status_code == 401


def test_upload_resume_with_existing_entries(
    client: TestClient, test_user: User, test_token: str, mock_resume_text, session
):
    """测试上传简历接口，当已有部分信息时"""
    # 添加一些已存在的用户资料
    existing_profile = UserProfile(
        user_id=test_user.id, category="resume_tech_stack", content="Python、Java、Go"
    )
    session.add(existing_profile)
    session.commit()

    # 创建测试文件
    test_file = BytesIO(mock_resume_text.encode("utf-8"))

    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("test_resume.txt", test_file, "text/plain")},
        headers={"Authorization": f"Bearer {test_token}"},
    )

    assert response.status_code == 200

    result = response.json()
    assert "msg" in result
    assert "new_entries" in result

    # 验证返回消息
    assert result["msg"] in ["简历解析成功", "简历解析完成，但未提取到有效信息"]

    # 验证新增条目数应该小于总条目数
    assert isinstance(result["new_entries"], int)
    assert result["new_entries"] >= 0


def test_upload_resume_empty_file(client: TestClient, test_user: User, test_token: str):
    """测试上传空简历文件"""
    # 创建空测试文件
    test_file = BytesIO(b"")

    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("empty_resume.txt", test_file, "text/plain")},
        headers={"Authorization": f"Bearer {test_token}"},
    )

    assert response.status_code == 200

    result = response.json()
    assert "msg" in result
    assert "new_entries" in result

    # 空文件应该返回简历解析失败
    assert result["msg"] == "简历解析失败"

    # 验证新增条目数
    assert isinstance(result["new_entries"], int)
    assert result["new_entries"] == 0
