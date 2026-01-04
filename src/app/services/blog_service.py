# app/services/blog_service.py

from core.rag_engine import rag_engine
from core.llm_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


async def chat_with_blog(query: str):
    # 1. 检索 (Retrieval)
    # 搜索最相关的 3 个片段
    search_results = rag_engine.search(query, top_k=3)

    if not search_results:
        return {"answer": "抱歉，我在知识库中没有找到相关内容。", "sources": []}

    # 2. 拼接上下文 (Context)
    context_str = ""
    sources = set()

    for i, item in enumerate(search_results):
        context_str += (
            f"--- 片段 {i + 1} (来源: {item['source']}) ---\n{item['content']}\n\n"
        )
        sources.add(item["source"])

    # 3. 构建 Prompt
    llm = get_llm(temperature=0.3)  # 问答模式温度低一点，防止胡编

    prompt = ChatPromptTemplate.from_template(
        """
        你是一个基于个人技术博客的 AI 助手。请根据下面的【参考片段】回答用户的问题。

        【规则】：        1. 必须基于参考片段的内容回答。        2. 如果参考片段里没有答案，请直接说“博客中未提及相关内容”。        3. 回答要条理清晰，可以使用 Markdown 格式。        4. 所有生成内容必须使用中文。

        【参考片段】：
        {context}

        【用户问题】：
        {question}
        """
    )

    chain = prompt | llm | StrOutputParser()

    # 4. 生成回答 (Generation)
    answer = await chain.ainvoke({"context": context_str, "question": query})

    return {"answer": answer, "sources": list(sources)}  # 返回去重后的文章列表
