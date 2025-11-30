import asyncio
from app.services.interview_service import generate_interview_guide
from app.schemas.interview import JDRequest


# 引入评分逻辑 (比如调用 GPT-4 打分)

async def run_benchmark():
    jds = load_test_jds()
    scores = []

    for jd in jds:
        # 1. 运行你的 Agent
        report = await generate_interview_guide(JDRequest(jd_text=jd['text']), ...)

        # 2. 评分：比对生成的题目和 JD 的相关性
        score = rate_with_gpt4(jd['text'], report.tech_questions)
        scores.append(score)

    print(f"平均得分: {sum(scores) / len(scores)}")