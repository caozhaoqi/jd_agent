from typing import List
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from app.core.llm_factory import get_llm


# 定义输出结构 (复用之前的 UserFact 逻辑)
class UserFact(BaseModel):
    category: str = Field(description="类别: tech_stack(技术栈)/experience(经验)/education(学历)/project(项目)")
    content: str = Field(description="事实内容")


class ResumeAnalysis(BaseModel):
    facts: List[UserFact] = Field(description="提取出的事实列表")


async def extract_resume_features(resume_text: str) -> List[UserFact]:
    """
    利用 LLM 从简历中提取关键画像
    """
    llm = get_llm(temperature=0)  # 提取信息要绝对严谨
    parser = PydanticOutputParser(pydantic_object=ResumeAnalysis)

    prompt = ChatPromptTemplate.from_template(
        """
        你是一位资深的简历分析师。请从以下【简历文本】中提取关键的用户画像信息，用于构建长期记忆。

        【简历文本】：
        {resume_text}

        【提取要求】：
        1. **tech_stack**: 提取核心编程语言、框架、工具（如 Python, FastAPI, Docker）。
        2. **experience**: 提取总工作年限、核心职能（如 "5年后端开发经验"）。
        3. **education**: 提取最高学历、专业（如 "本科 计算机科学"）。
        4. **project**: 简要总结 1-2 个核心项目的亮点（一句话概括）。
        5. 不要提取姓名、电话等隐私信息。

        请严格按照 JSON 格式输出:
        {format_instructions}
        """
    )

    chain = prompt | llm | parser

    try:
        # 截断简历过长内容，防止 token 溢出 (一般简历不会太长，取前 3000 字符足够)
        result = await chain.ainvoke({
            "resume_text": resume_text[:3000],
            "format_instructions": parser.get_format_instructions()
        })
        return result.facts
    except Exception as e:
        print(f"❌ Resume extraction failed: {e}")
        return []