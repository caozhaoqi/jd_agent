from app.core.llm_factory import get_llm


async def run_mock_interview(jd_text):
    interviewer = get_llm(system_prompt="你是严厉的面试官，请根据JD提问")
    candidate = get_llm(system_prompt="你是求职者，请根据简历回答")

    history = []

    # 第一轮
    q1 = await interviewer.ainvoke(f"JD内容: {jd_text}。请开始提问。")
    history.append(f"面试官: {q1}")

    # 第二轮
    a1 = await candidate.ainvoke(f"面试官问: {q1}。请回答。")
    history.append(f"求职者: {a1}")

    # 第三轮
    feedback = await get_llm().ainvoke(f"请点评这段对话的质量: {history}")

    return feedback