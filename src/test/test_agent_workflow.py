import json
import pytest
from fastapi.testclient import TestClient

# 注意：此处没有任何 from app... 的导入

def test_generate_guide_dynamic_flow(client: TestClient, test_user):
    """
    测试 /jd/generate-guide 接口是否能成功运行新的动态 Agent 工作流。
    'client' 和 'test_user' fixtures 由 conftest.py 提供。
    """
    # --- 延迟导入 ---
    # 仅在函数执行时才导入，此时环境变量已由 pytest_configure 加载
    from app.api.deps import get_current_user

    # 通过 client.app 访问 FastAPI 实例来覆盖依赖
    client.app.dependency_overrides[get_current_user] = lambda: test_user

    # 准备测试数据
    jd_text = "招聘一名熟悉 Python 和 FastAPI 的后端开发工程师，要求3年经验。"
    request_data = {"jd_text": jd_text}

    # 发送请求
    response = client.post("/api/v1/jd/generate-guide", json=request_data)

    # 断言：HTTP 状态码
    assert response.status_code == 200, f"请求失败，状态码: {response.status_code}, 内容: {response.text}"

    # 断言：流式响应内容
    stream_content = response.text
    lines = stream_content.strip().split('\n\n')
    
    events = []
    for line in lines:
        if line.startswith("data:"):
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                events.append({"type": "DONE"})
                break
            try:
                events.append(json.loads(data_str))
            except json.JSONDecodeError:
                pytest.fail(f"无法解析流式数据中的JSON: {data_str}")

    # 检查是否包含调度器节点的思考步骤
    router_thought_found = any(
        event.get("type") == "thought" and "调度器" in event.get("content", "")
        for event in events
    )
    assert router_thought_found, "流式响应中未找到'调度器'节点的思考步骤，高级Agent流程可能未生效"

    # 检查是否包含最终结果
    result_found = any(event.get("type") == "result" for event in events)
    assert result_found, "流式响应中未找到最终的'result'事件"

    # 检查是否以 [DONE] 结束
    assert events and events[-1].get("type") == "DONE", "流式响应未以'[DONE]'结束"

    # 清理依赖覆盖
    client.app.dependency_overrides = {}

    print("\n✅ Agent 动态工作流测试通过！")
    print(f"   - 共接收到 {len(events)} 个流式事件。")
    print(f"   - 已验证'调度器'节点被成功调用。")
    print(f"   - 已验证流程正常结束。")
