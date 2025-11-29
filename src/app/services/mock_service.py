import asyncio
import json
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.llm_factory import get_llm
from app.chains.mock_agents import get_interviewer_chain, get_candidate_chain


def format_sse(role: str, content: str) -> str:
    """格式化为 SSE 数据包"""
    data = {
        "role": role,  # 'interviewer', 'candidate', 'system', 'reviewer'
        "content": content
    }
    # ensure_ascii=False 保证中文正常显示
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_mock_interview_stream(jd_text: str, rounds: int = 3):
    """
    生成器函数：控制面试流程并流式输出
    """
    # 1. 初始化 Agents
    interviewer = get_interviewer_chain()
    candidate = get_candidate_chain()

    # 2. 初始化点评 Agent (Reviewer)
    reviewer_llm = get_llm(temperature=0.3)  # 点评需要客观
    reviewer_prompt = ChatPromptTemplate.from_template(
        """
        你是一位资深的技术面试教练。请阅读以下模拟面试的记录，对候选人的表现进行专业点评。

        【面试记录】：
        {history}

        【点评要求】：
        1. 给出一个综合评分（0-100分）。
        2. 列出 2-3 个候选人的亮点（Strengths）。
        3. 列出 2-3 个候选人需要改进的地方（Weaknesses），并给出具体建议。
        4. 语气要客观、中肯。
        """
    )
    reviewer_chain = reviewer_prompt | reviewer_llm | StrOutputParser()

    chat_history = []  # 记录上下文

    # 3. 开场白
    yield format_sse("system", "🚀 模拟面试开始！面试官正在阅读简历...")
    await asyncio.sleep(1)

    # 4. 循环面试轮次
    for i in range(rounds):
        # --- Round i: 面试官提问 ---
        history_str = "\n".join(chat_history)
        yield format_sse("system", f"🎤 第 {i + 1} 轮提问中...")

        # 面试官思考
        question = await interviewer.ainvoke({
            "jd_text": jd_text,
            "history": history_str
        })

        chat_history.append(f"面试官: {question}")
        yield format_sse("interviewer", question)

        # --- Round i: 候选人回答 ---
        yield format_sse("system", "🤔 候选人思考中...")
        await asyncio.sleep(1.5)  # 模拟思考时间

        # 候选人回答
        answer = await candidate.ainvoke({"question": question})

        chat_history.append(f"候选人: {answer}")
        yield format_sse("candidate", answer)

        await asyncio.sleep(1)

    # 5. 生成点评报告 (Planning/Reflection)
    yield format_sse("system", "👨‍🏫 面试结束，面试官正在撰写评估报告...")

    # 将完整的对话记录喂给 Reviewer
    full_history = "\n".join(chat_history)
    review_content = await reviewer_chain.ainvoke({"history": full_history})

    # 推送点评结果
    yield format_sse("reviewer", review_content)

    # 6. 发送结束信号 (一定要放在最后！)
    yield format_sse("done", "[DONE]")