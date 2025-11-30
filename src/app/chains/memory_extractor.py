from typing import List
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from app.core.llm_factory import get_llm
from loguru import logger

# 定义输出结构
class UserFact(BaseModel):
    category: str = Field(description="类别: tech_stack/experience/preference/other")
    content: str = Field(description="提炼出的事实，简短有力")


class UserProfileUpdate(BaseModel):
    new_facts: List[UserFact] = Field(description="提取出的新事实列表")


async def extract_user_profile(chat_history: str) -> List[UserFact]:
    """
    从对话历史中提炼用户画像
    """
    llm = get_llm(temperature=0.1)  # 提取事实要严谨
    parser = PydanticOutputParser(pydantic_object=UserProfileUpdate)

    prompt = ChatPromptTemplate.from_template(
        """
        你是一个专业的个人信息分析师。请阅读以下【对话记录】，提取关于用户的关键信息，用于构建用户画像（长期记忆）。

        【对话记录】：
        {chat_history}

        【提取原则】：
        1. 只提取**长期有效**的信息（如技术栈、工作年限、求职偏好）。
        2. 忽略临时的闲聊（如“你好”、“谢谢”）。
        3. 如果没有有价值的信息，返回空列表。
        4. 类别仅限于：tech_stack（技术栈）、experience（经验）、preference（偏好）。

        请严格按照 JSON 格式输出:
        {format_instructions}
        """
    )

    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({
            "chat_history": chat_history,
            "format_instructions": parser.get_format_instructions()
        })
        return result.new_facts
    except Exception as e:
        logger.debug(f"❌ Memory extraction failed: {e}")
        return []