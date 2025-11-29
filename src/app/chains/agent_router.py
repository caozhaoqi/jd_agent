from app.core.llm_factory import get_llm
from app.core.tools import search_blog_tool, search_company_tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate


def create_jd_agent():
    llm = get_llm(temperature=0)

    # 告诉大模型：你有这两个工具可以用
    tools = [search_blog_tool, search_company_tool]

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的招聘助手。你会根据用户的需求，自主决定是否需要查阅知识库或调查公司背景。"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),  # AI 的思考过程会填在这里
    ])

    # 创建 Agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    return agent_executor

# 使用
# agent = create_jd_agent()
# response = agent.invoke({"input": "帮我分析下神州邦邦这个公司"})
# -> Agent 会自动决定调用 search_company_tool