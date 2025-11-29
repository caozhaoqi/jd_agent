from typing import List
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from app.core.llm_factory import get_llm
from app.schemas.interview import InterviewQuestion
from app.utils.logger import logger


# 辅助模型
class QuestionList(BaseModel):
    questions: List[InterviewQuestion]


async def critique_tech_questions_async(
        original_questions: List[InterviewQuestion],
        level: str
) -> List[InterviewQuestion]:
    """
    反思环节：检查生成的题目是否符合职级要求，如果不符合则修改。
    """
    logger.info(f"🤔 [Reflection] Critiquing {len(original_questions)} questions for level: {level}...")

    # 1. 准备数据：把对象转成文本喂给 LLM
    questions_text = "\n".join([f"Q: {q.question}\nA: {q.reference_answer}" for q in original_questions])

    # 2. 设置 LLM (建议用 Smart 模型，如 GPT-4/DeepSeek-V3，温度稍低)
    llm = get_llm(temperature=0.3)
    parser = PydanticOutputParser(pydantic_object=QuestionList)

    # 3. 编写“反思” Prompt
    prompt = ChatPromptTemplate.from_template(
        """
        你是一个严厉的技术面试官主管。请审核以下初级面试官生成的面试题。

        【目标候选人职级】：{level}

        【待审核题目】：
        {questions_text}

        【审核标准】：
        1. 难度匹配：如果候选人是高级/资深，题目不能问基础语法，必须问底层原理或架构设计。
        2. 准确性：参考回答必须准确无误。
        3. 深度：题目不能太宽泛，要有具体的考察点。

        【任务】：
        - 如果题目质量合格，直接保留原题。
        - **如果题目太简单或有逻辑错误，请重写该题目和答案，使其更具挑战性。**
        - 保持题目数量不变。

        请严格按照 JSON 格式输出修正后的题目列表:
        {format_instructions}
        """
    )

    chain = prompt | llm | parser

    try:
        # 4. 执行反思
        result = await chain.ainvoke({
            "level": level,
            "questions_text": questions_text,
            "format_instructions": parser.get_format_instructions()
        })
        logger.success("✨ [Reflection] Questions refined successfully.")
        return result.questions

    except Exception as e:
        logger.warning(f"⚠️ [Reflection] Critique failed, returning original questions. Error: {e}")
        # 如果反思步骤挂了（比如 Token 超限），为了系统稳定性，降级返回原题
        return original_questions