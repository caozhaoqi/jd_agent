from typing import List
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from app.core.llm_factory import get_llm
from app.schemas.interview import InterviewQuestion


# 辅助模型：用于解析列表
class QuestionList(BaseModel):
    questions: List[InterviewQuestion]


# 异步生成技术题
async def generate_tech_async(tech_stack: List[str], level: str) -> List[InterviewQuestion]:
    llm = get_llm(temperature=0.7)
    parser = PydanticOutputParser(pydantic_object=QuestionList)

    prompt = ChatPromptTemplate.from_template(
        """
        基于以下技术栈: {tech_stack}
        针对 {level} 级别的候选人，生成 3 道具有挑战性的技术面试题。

        要求：
        1. 题目要有深度，考察底层原理或实战排错。
        2. 每道题都要提供简练的参考回答要点。
        3. 类别标记为 'Technical'。

        请严格按照 JSON 格式输出:
        {format_instructions}
        """
    )

    chain = prompt | llm | parser

    # 使用 ainvoke 并行等待
    result = await chain.ainvoke({
        "tech_stack": ", ".join(tech_stack),
        "level": level,
        "format_instructions": parser.get_format_instructions()
    })

    return result.questions