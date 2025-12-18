from typing import List
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel
from app.core.llm_factory import get_llm
from app.schemas.interview import InterviewQuestion


# 辅助模型：用于解析列表
class QuestionList(BaseModel):
    questions: List[InterviewQuestion]


# ✅ 新增：清洗函数，去除 Markdown 代码块标记
def clean_json_output(text: str) -> str:
    text = text.strip()
    # 移除 ```json 和 结尾的 ```
    if "```json" in text:
        text = text.split("```json")[1]
    elif "```" in text:
        text = text.split("```")[1]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


# 异步生成技术题
async def generate_tech_async(
    tech_stack: List[str],
    level: str,
    kb_context: str = "",
    chat_history: list = [],
    user_profile: str = "",
) -> List[InterviewQuestion]:
    llm = get_llm(temperature=0.7)
    parser = PydanticOutputParser(pydantic_object=QuestionList)

    # 动态构建 Prompt
    context_str = ""
    if kb_context:
        context_str += f"\n[参考知识库]:\n{kb_context[:1500]}\n"  # 限制知识库长度
    if user_profile:
        context_str += f"\n[候选人画像]:\n{user_profile}\n"

    prompt = ChatPromptTemplate.from_template(
        """
        你是一个专业技术面试官。
        请基于以下信息生成 3 道核心技术面试题。

        候选人技术栈: {tech_stack}
        目标职级: {level}
        {context_str}

        要求：
        1. 题目考察核心技术原理或实战能力。
        2. 结合知识库内容（如果有）进行针对性提问。
        3. 严格按照 JSON 格式输出，不要包含 Markdown 代码块标记。
        4. 所有生成内容必须使用中文，包括问题和答案。

        输出格式要求:
        {format_instructions}
        """
    )

    # ✅ 关键修改：构造 Chain
    # 1. Prompt -> LLM -> StrOutputParser (拿到纯文本)
    # 2. -> RunnableLambda(clean) (去除 ```json)
    # 3. -> parser (Pydantic 解析)
    chain = (
        prompt | llm | StrOutputParser() | RunnableLambda(clean_json_output) | parser
    )

    try:
        result = await chain.ainvoke(
            {
                "tech_stack": ", ".join(tech_stack),
                "level": level,
                "context_str": context_str,
                "format_instructions": parser.get_format_instructions(),
            }
        )
        return result.questions
    except Exception as e:
        print(f"❌ Tech Gen Parse Error: {e}")
        # 兜底返回空列表，防止程序崩溃
        return []
