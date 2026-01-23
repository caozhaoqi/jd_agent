from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.llm_factory import get_llm
from core.config import settings


def get_interviewer_chain(interview_type: str = "comprehensive"):
    """面试官 Agent：负责提问"""
    llm = get_llm(temperature=0.7, model=settings.MODEL_NAME)  # 面试官可以灵活一点

    # 根据面试类型选择不同的角色和问题类型
    interviewer_roles = {
        "tech": "技术面试官",
        "hr": "HR面试官",
        "comprehensive": "综合面试官",
        "behavioral": "行为面试官",
        "management": "管理面试官",
    }

    question_types = {
        "tech": "技术问题",
        "hr": "HR问题",
        "comprehensive": "面试问题",
        "behavioral": "行为问题",
        "management": "管理问题",
    }

    role = interviewer_roles.get(interview_type, "综合面试官")
    q_type = question_types.get(interview_type, "面试问题")

    # 直接将role和q_type嵌入到提示模板中，而不是作为模板变量
    prompt_template = f"""
    你是一位严厉但专业的{role}。

    【岗位 JD】：
    {{jd_text}}

    【当前面试进展】：
    {{history}}

    请根据 JD 和刚才的对话，向候选人提出**下一个**{q_type}。
    要求：
    1. 问题要简短有力，不要废话。
    2. 如果候选人上一题回答得不好，可以追问；如果回答得好，进入下一个相关要点。
    3. 只需要输出问题本身，不要输出 "好的"、"下一题" 等前缀。
    """

    prompt = ChatPromptTemplate.from_template(prompt_template)
    return prompt | llm | StrOutputParser()


def get_candidate_chain():
    """候选人 Agent：负责回答"""
    llm = get_llm(temperature=0.5, model=settings.MODEL_NAME)  # 候选人要稳重

    prompt = ChatPromptTemplate.from_template(
        """
        你是一位经验丰富的高级工程师，正在参加面试。

        【面试官的问题】：
        {question}

        请回答这个问题。
        要求：
        1. 回答要有逻辑，采用 STAR 法则或分点作答。
        2. 表现出自信，适当展示深度。
        3. 回答长度控制在 200 字以内，不要长篇大论。
        """
    )
    return prompt | llm | StrOutputParser()
