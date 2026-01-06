import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from loguru import logger


class ReportExportService:
    """面试报告导出服务"""
    
    @staticmethod
    def _format_meta(meta_info: Optional[Dict[str, Any]]) -> str:
        """格式化元数据"""
        if not meta_info:
            return ""
        
        lines = ["## 面试基本信息", ""]
        if meta_info.get("company_name"):
            lines.append(f"- **公司名称**: {meta_info['company_name']}")
        if meta_info.get("tech_stack"):
            lines.append(f"- **技术栈**: {', '.join(meta_info['tech_stack'])}")
        if meta_info.get("years_required"):
            lines.append(f"- **工作年限要求**: {meta_info['years_required']}")
        if meta_info.get("soft_skills"):
            lines.append(f"- **软技能要求**: {', '.join(meta_info['soft_skills'])}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_questions(questions: Optional[list], title: str) -> str:
        """格式化问题列表"""
        if not questions:
            return ""
        
        lines = [f"## {title}", ""]
        for i, q in enumerate(questions, 1):
            category = q.get("category", "通用")
            question = q.get("question", "")
            answer = q.get("reference_answer", "")
            
            lines.append(f"### {i}. [{category}] {question}")
            lines.append(f"**参考回答**: {answer}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_evaluation(overall_score: Optional[int], strengths: Optional[list], improvements: Optional[list]) -> str:
        """格式化评估结果"""
        lines = ["## 面试评估", ""]
        
        if overall_score is not None:
            lines.append(f"**综合评分**: {overall_score}/100")
            score_level = "优秀" if overall_score >= 80 else "良好" if overall_score >= 60 else "需改进"
            lines.append(f"**评级**: {score_level}")
            lines.append("")
        
        if strengths:
            lines.append("### 关键优势")
            for s in strengths:
                lines.append(f"- {s}")
            lines.append("")
        
        if improvements:
            lines.append("### 改进建议")
            for i in improvements:
                lines.append(f"- {i}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_markdown(
        report_title: str,
        company_name: Optional[str],
        position: Optional[str],
        meta_info: Optional[Dict[str, Any]],
        tech_questions: Optional[List[Dict[str, Any]]],
        hr_questions: Optional[List[Dict[str, Any]]],
        company_analysis: Optional[str],
        overall_score: Optional[int],
        key_strengths: Optional[List[str]],
        areas_for_improvement: Optional[List[str]]
    ) -> str:
        """生成Markdown格式报告"""
        
        lines = [
            f"# {report_title}",
            "",
            f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            ""
        ]
        
        if company_name:
            lines.append(f"**公司**: {company_name}")
        if position:
            lines.append(f"**职位**: {position}")
        lines.append("")
        
        if company_analysis:
            lines.append("## 公司背景分析")
            lines.append(company_analysis)
            lines.append("")
        
        lines.append(ReportExportService._format_meta(meta_info))
        lines.append("")
        
        lines.append(ReportExportService._format_questions(tech_questions, "技术面试题"))
        lines.append("")
        
        lines.append(ReportExportService._format_questions(hr_questions, "HR面试题"))
        lines.append("")
        
        if overall_score is not None or key_strengths or areas_for_improvement:
            lines.append(ReportExportService._format_evaluation(overall_score, key_strengths, areas_for_improvement))
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_html(
        report_title: str,
        company_name: Optional[str],
        position: Optional[str],
        meta_info: Optional[Dict[str, Any]],
        tech_questions: Optional[List[Dict[str, Any]]],
        hr_questions: Optional[List[Dict[str, Any]]],
        company_analysis: Optional[str],
        overall_score: Optional[int],
        key_strengths: Optional[List[str]],
        areas_for_improvement: Optional[List[str]]
    ) -> str:
        """生成HTML格式报告"""
        
        html_lines = [
            "<!DOCTYPE html>",
            "<html lang='zh-CN'>",
            "<head>",
            f"    <meta charset='UTF-8'>",
            f"    <title>{report_title}</title>",
            "    <style>",
            "        body { font-family: 'Microsoft YaHei', Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }",
            "        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }",
            "        h2 { color: #34495e; border-left: 4px solid #3498db; padding-left: 10px; margin-top: 30px; }",
            "        h3 { color: #7f8c8d; margin-top: 20px; }",
            "        .meta { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }",
            "        .question { background: #fff; border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px; }",
            "        .category { display: inline-block; background: #3498db; color: white; padding: 3px 10px; border-radius: 3px; font-size: 12px; }",
            "        .answer { background: #f0f8ff; padding: 10px; margin-top: 10px; border-radius: 3px; }",
            "        .score { font-size: 24px; color: #27ae60; font-weight: bold; }",
            "        .strengths { color: #27ae60; }",
            "        .improvements { color: #e74c3c; }",
            "        ul { padding-left: 20px; }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>{report_title}</h1>",
            f"    <p><em>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>",
        ]
        
        if company_name or position:
            html_lines.append("    <div class='meta'>")
            if company_name:
                html_lines.append(f"        <p><strong>公司:</strong> {company_name}</p>")
            if position:
                html_lines.append(f"        <p><strong>职位:</strong> {position}</p>")
            html_lines.append("    </div>")
        
        if company_analysis:
            html_lines.append("    <h2>公司背景分析</h2>")
            html_lines.append(f"    <p>{company_analysis}</p>")
        
        if meta_info:
            html_lines.append("    <h2>面试基本信息</h2>")
            html_lines.append("    <div class='meta'>")
            if meta_info.get("tech_stack"):
                html_lines.append(f"        <p><strong>技术栈:</strong> {', '.join(meta_info['tech_stack'])}</p>")
            if meta_info.get("years_required"):
                html_lines.append(f"        <p><strong>工作年限要求:</strong> {meta_info['years_required']}</p>")
            html_lines.append("    </div>")
        
        if tech_questions:
            html_lines.append("    <h2>技术面试题</h2>")
            for i, q in enumerate(tech_questions, 1):
                category = q.get("category", "通用")
                question = q.get("question", "")
                answer = q.get("reference_answer", "")
                
                html_lines.extend([
                    f"    <div class='question'>",
                    f"        <span class='category'>{category}</span>",
                    f"        <h3>{i}. {question}</h3>",
                    f"        <div class='answer'><strong>参考回答:</strong> {answer}</div>",
                    "    </div>"
                ])
        
        if hr_questions:
            html_lines.append("    <h2>HR面试题</h2>")
            for i, q in enumerate(hr_questions, 1):
                category = q.get("category", "通用")
                question = q.get("question", "")
                answer = q.get("reference_answer", "")
                
                html_lines.extend([
                    f"    <div class='question'>",
                    f"        <span class='category'>{category}</span>",
                    f"        <h3>{i}. {question}</h3>",
                    f"        <div class='answer'><strong>参考回答:</strong> {answer}</div>",
                    "    </div>"
                ])
        
        if overall_score is not None or key_strengths or areas_for_improvement:
            html_lines.append("    <h2>面试评估</h2>")
            html_lines.append("    <div class='meta'>")
            if overall_score is not None:
                html_lines.append(f"        <p class='score'>综合评分: {overall_score}/100</p>")
            if key_strengths:
                html_lines.append("        <p><strong>关键优势:</strong></p>")
                html_lines.append("        <ul class='strengths'>")
                for s in key_strengths:
                    html_lines.append(f"            <li>{s}</li>")
                html_lines.append("        </ul>")
            if areas_for_improvement:
                html_lines.append("        <p><strong>改进建议:</strong></p>")
                html_lines.append("        <ul class='improvements'>")
                for i in areas_for_improvement:
                    html_lines.append(f"            <li>{i}</li>")
                html_lines.append("        </ul>")
            html_lines.append("    </div>")
        
        html_lines.extend([
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_lines)
    
    @staticmethod
    def generate_text(
        report_title: str,
        company_name: Optional[str],
        position: Optional[str],
        meta_info: Optional[Dict[str, Any]],
        tech_questions: Optional[List[Dict[str, Any]]],
        hr_questions: Optional[List[Dict[str, Any]]],
        company_analysis: Optional[str],
        overall_score: Optional[int],
        key_strengths: Optional[List[str]],
        areas_for_improvement: Optional[List[str]]
    ) -> str:
        """生成纯文本格式报告"""
        
        lines = [
            "=" * 60,
            report_title,
            "=" * 60,
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        if company_name:
            lines.append(f"公司: {company_name}")
        if position:
            lines.append(f"职位: {position}")
        lines.append("")
        
        if company_analysis:
            lines.append("-" * 40)
            lines.append("公司背景分析")
            lines.append("-" * 40)
            lines.append(company_analysis)
            lines.append("")
        
        if meta_info:
            lines.append("-" * 40)
            lines.append("面试基本信息")
            lines.append("-" * 40)
            if meta_info.get("tech_stack"):
                lines.append(f"技术栈: {', '.join(meta_info['tech_stack'])}")
            if meta_info.get("years_required"):
                lines.append(f"工作年限要求: {meta_info['years_required']}")
            lines.append("")
        
        if tech_questions:
            lines.append("-" * 40)
            lines.append("技术面试题")
            lines.append("-" * 40)
            for i, q in enumerate(tech_questions, 1):
                category = q.get("category", "通用")
                question = q.get("question", "")
                answer = q.get("reference_answer", "")
                lines.append(f"{i}. [{category}] {question}")
                lines.append(f"   参考回答: {answer}")
                lines.append("")
        
        if hr_questions:
            lines.append("-" * 40)
            lines.append("HR面试题")
            lines.append("-" * 40)
            for i, q in enumerate(hr_questions, 1):
                category = q.get("category", "通用")
                question = q.get("question", "")
                answer = q.get("reference_answer", "")
                lines.append(f"{i}. [{category}] {question}")
                lines.append(f"   参考回答: {answer}")
                lines.append("")
        
        if overall_score is not None or key_strengths or areas_for_improvement:
            lines.append("-" * 40)
            lines.append("面试评估")
            lines.append("-" * 40)
            if overall_score is not None:
                lines.append(f"综合评分: {overall_score}/100")
            if key_strengths:
                lines.append("关键优势:")
                for s in key_strengths:
                    lines.append(f"  - {s}")
            if areas_for_improvement:
                lines.append("改进建议:")
                for i in areas_for_improvement:
                    lines.append(f"  - {i}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append("报告结束")
        lines.append("=" * 60)
        
        return "\n".join(lines)


export_service = ReportExportService()
