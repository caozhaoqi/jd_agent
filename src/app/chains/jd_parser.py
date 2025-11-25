from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from app.core.llm_factory import get_llm
from app.schemas.interview import JDMetaData


# 异步解析函数
async def parse_jd_async(jd_text: str) -> JDMetaData:
    # 解析任务通常不需要太高创造性，温度设为 0
    llm = get_llm(temperature=0)
    parser = PydanticOutputParser(pydantic_object=JDMetaData)

    prompt = ChatPromptTemplate.from_template(
        """
        你是一个专业的招聘专家。请分析以下岗位描述（JD），提取关键信息。

        JD 内容:
        {jd_text}

        请严格按照以下格式输出 JSON:
        {format_instructions}
        """
    )

    chain = prompt | llm | parser

    # 注意：这里使用的是 ainvoke (Async Invoke)
    result = await chain.ainvoke({
        "jd_text": jd_text,
        "format_instructions": parser.get_format_instructions()
    })

    return result