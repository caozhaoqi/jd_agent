from typing import List
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel
from core.llm_factory import get_llm
from core.config import settings
from schemas.interview import InterviewQuestion
from utils.text_utils import clean_json_output  # 导入重构后的函数

# 辅助模型
class QuestionList(BaseModel):
    questions: List[InterviewQuestion]


async def generate_hr_async(
    soft_skills: List[str], company_info: str = ""
) -> List[InterviewQuestion]:
    """
    异步生成 HR 行为面试题
    :param soft_skills: JD 中提取的软技能列表
    :param company_info: (可选) 公司背景调研信息
    """
    llm = get_llm(temperature=0.8, model=settings.MODEL_NAME)  # HR 题目可以灵活一点
    parser = PydanticOutputParser(pydantic_object=QuestionList)

    # 动态构建上下文
    context_str = ""
    if company_info:
        context_str = f"已知该公司背景如下：{company_info[:1000]}"  # 限制公司背景长度

    prompt = ChatPromptTemplate.from_template(
        """
        你是一个专业 HR 面试官。
        {context_str}

        该岗位要求的软技能包括: {soft_skills}

        请设计 1-2 道行为面试题，要求：
        1. 基于 STAR 法则设计。
        2. 如果提供了公司背景，尝试结合公司文化提问。
        3. 类别标记为 'HR/Behavioral'。
        4. 严格按照 JSON 格式输出，不要包含 Markdown 代码块。
        5. 所有生成内容必须使用中文。

        请严格按照 JSON 格式输出:
        {format_instructions}
        """
    )

    # 构造包含清洗步骤的 Chain
    chain = (
        prompt | llm | StrOutputParser() | RunnableLambda(clean_json_output) | parser
    )

    try:
        result = await chain.ainvoke(
            {
                "context_str": context_str,
                "soft_skills": ", ".join(soft_skills),
                "format_instructions": parser.get_format_instructions(),
            }
        )
        return result.questions
    except Exception as e:
        print(f"❌ HR Gen Parse Error: {e}")
        return []
