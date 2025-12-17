from typing import List, Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from app.core.llm_factory import get_llm
from loguru import logger


class MatchItem(BaseModel):
    """单个匹配项"""
    category: str = Field(description="匹配类别: tech_stack(技术栈)/experience(经验)/education(学历)/skills(技能)")
    resume_content: str = Field(description="简历中的相关内容")
    jd_content: str = Field(description="JD中的相关要求")
    match_degree: int = Field(description="匹配度 0-100")
    match_type: str = Field(description="匹配类型: exact(完全匹配)/partial(部分匹配)/none(不匹配)")


class MatchAnalysis(BaseModel):
    """匹配分析结果"""
    overall_score: int = Field(description="总体匹配度 0-100")
    strengths: List[str] = Field(description="简历的优势")
    weaknesses: List[str] = Field(description="简历的不足")
    suggestions: List[str] = Field(description="简历优化建议")
    detailed_matches: List[MatchItem] = Field(description="详细匹配项列表")


async def match_resume_with_jd(resume_text: str, jd_text: str) -> Dict[str, Any]:
    """
    利用LLM分析简历与JD的匹配度
    
    Args:
        resume_text: 简历文本
        jd_text: JD文本
    
    Returns:
        包含匹配度分析的字典
    """
    llm = get_llm(temperature=0.1)  # 适当的随机性，保证分析的灵活性
    parser = PydanticOutputParser(pydantic_object=MatchAnalysis)

    prompt = ChatPromptTemplate.from_template(
        """
        你是一位专业的招聘顾问，请严格分析以下简历与JD的匹配度。
        
        【简历文本】：
        {resume_text}
        
        【JD文本】：
        {jd_text}
        
        【分析要求】：
        1. **总体匹配度**：从0-100分评估简历与JD的整体匹配程度
        2. **详细匹配分析**：
           - 技术栈(tech_stack)：分析编程语言、框架、工具的匹配情况
           - 经验(experience)：分析工作年限、项目经验与JD要求的匹配情况
           - 学历(education)：分析学历、专业与JD要求的匹配情况
           - 技能(skills)：分析软技能、硬技能与JD要求的匹配情况
        3. **优势(strengths)**：列出简历中符合或超过JD要求的亮点
        4. **不足(weaknesses)**：列出简历中不符合或缺少JD要求的地方
        5. **优化建议(suggestions)**：提供具体的简历优化建议，帮助提高匹配度
        
        【输出格式要求】：
        - 详细匹配项中，每个匹配项需包含：类别、简历内容、JD内容、匹配度(0-100)、匹配类型(exact/partial/none)
        - 优势、不足、建议每项不超过20字，简洁明了
        
        请严格按照以下JSON格式输出：
        {format_instructions}
        """
    )

    chain = prompt | llm | parser

    try:
        # 截断过长内容，防止token溢出
        result = await chain.ainvoke({
            "resume_text": resume_text[:3000],
            "jd_text": jd_text[:3000],
            "format_instructions": parser.get_format_instructions()
        })
        
        # 转换为字典格式返回
        return result.model_dump()
    except Exception as e:
        logger.error(f"❌ Resume-JD matching failed: {e}")
        # 返回默认错误结果
        return {
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "detailed_matches": []
        }
