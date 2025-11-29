from typing import List, Optional
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from app.core.llm_factory import get_llm
from app.schemas.interview import InterviewQuestion


# 辅助模型：用于解析列表
class QuestionList(BaseModel):
    questions: List[InterviewQuestion]


async def generate_tech_async(
        tech_stack: List[str],
        level: str,
        kb_context: str = "",
        chat_history: List[str] = None,
        user_profile: str = "",  # 接收参数
) -> List[InterviewQuestion]:
    # 1. 处理默认值
    if chat_history is None:
        chat_history = []

    # 2. 拼接历史记录字符串
    history_str = "\n".join(chat_history[-5:]) if chat_history else "无历史对话"

    llm = get_llm(temperature=0.7)
    parser = PydanticOutputParser(pydantic_object=QuestionList)

    # 3. 动态构建上下文指令
    context_instruction = ""
    if kb_context:
        context_instruction = f"""
        【参考知识库】：
        以下是该用户个人博客中的相关技术笔记，请优先参考这些内容来出题：
        {kb_context}
        """

    # 4. 构建 Prompt
    prompt = ChatPromptTemplate.from_template(
        """
        你是一个资深技术面试官。

        【当前任务】：
        基于技术栈 [{tech_stack}] 和职级 [{level}] 生成 3 道面试题。

        {context_instruction}

        {user_profile}

        【历史对话上下文（Memory）】：
        {history_str}
        (注意：如果用户在历史对话中指出了偏好，请遵循；否则请忽略)

        【要求】：
        1. 题目要有深度，考察底层原理或实战排错。
        2. 每道题都要提供简练的参考回答要点。
        3. 类别标记为 'Technical'。

        请严格按照 JSON 格式输出:
        {format_instructions}
        """
    )

    chain = prompt | llm | parser

    # 5. 执行 (🔴 核心修复：必须把 user_profile 传进去！)
    result = await chain.ainvoke({
        "tech_stack": ", ".join(tech_stack),
        "level": level,
        "history_str": history_str,
        "user_profile": user_profile,  # <--- 之前漏了这行，导致 KeyError
        "context_instruction": context_instruction,
        "format_instructions": parser.get_format_instructions()
    })

    return result.questions