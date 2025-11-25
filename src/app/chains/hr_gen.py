from typing import List
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from app.core.llm_factory import get_llm
from app.schemas.interview import InterviewQuestion


# 辅助模型
class QuestionList(BaseModel):
    questions: List[InterviewQuestion]


async def generate_hr_async(soft_skills: List[str], company_info: str = "") -> List[InterviewQuestion]:
    """
    异步生成 HR 行为面试题
    :param soft_skills: JD 中提取的软技能列表
    :param company_info: (可选) 公司背景调研信息
    """
    llm = get_llm(temperature=0.8)  # HR 题目可以灵活一点
    parser = PydanticOutputParser(pydantic_object=QuestionList)

    # 动态构建上下文
    context_str = ""
    if company_info:
        context_str = f"已知该公司背景如下：{company_info}"

    prompt = ChatPromptTemplate.from_template(
        """
        你是一个资深 HR 面试官。
        {context_str}

        该岗位要求的软技能包括: {soft_skills}

        请设计 2 道行为面试题（Behavioral Questions），要求：
        1. 基于 STAR 法则（情境、任务、行动、结果）设计。
        2. 如果提供了公司背景，请尝试结合公司文化提问。
        3. 类别标记为 'HR/Behavioral'。

        请严格按照 JSON 格式输出:
        {format_instructions}
        """
    )

    chain = prompt | llm | parser

    result = await chain.ainvoke({
        "context_str": context_str,
        "soft_skills": ", ".join(soft_skills),
        "format_instructions": parser.get_format_instructions()
    })

    return result.questions