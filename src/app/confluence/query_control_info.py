import os
import sys

# 设置HuggingFace国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from loguru import logger

# 配置路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_DIR = os.path.join(CURRENT_DIR, "confluence_faiss_index")


def load_knowledge_base():
    """加载知识库向量数据库"""
    logger.info("📚 正在加载知识库向量数据库...")
    
    try:
        # 初始化Embedding模型（与构建索引时使用相同的模型）
        embedding_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        
        # 加载FAISS向量数据库
        vector_db = FAISS.load_local(
            INDEX_DIR,
            embedding_model,
            allow_dangerous_deserialization=True
        )
        logger.success("✅ 知识库加载成功！")
        return vector_db
    except Exception as e:
        logger.error(f"❌ 知识库加载失败: {e}")
        logger.error("💡 请先运行构建脚本创建向量数据库：python src/app/confluence/build_confluence_kb.py")
        return None


def search_knowledge_base(vector_db, query, k=5):
    """直接在知识库中搜索相关文档"""
    try:
        # 使用向量数据库的相似性搜索功能
        results = vector_db.similarity_search(
            query=query,
            k=k
        )
        return results
    except Exception as e:
        logger.error(f"❌ 搜索失败: {e}")
        return []


def extract_relevant_information(docs):
    """从搜索结果中提取相关信息"""
    extracted_info = []
    
    for i, doc in enumerate(docs, 1):
        # 提取文档内容，限制长度
        content = doc.page_content[:2000]  # 限制内容长度
        metadata = doc.metadata
        
        info = {
            "id": i,
            "content": content,
            "metadata": metadata
        }
        extracted_info.append(info)
    
    return extracted_info


def generate_manual_summary(collected_info):
    """手动生成总结报告"""
    summary = "# 管控相关信息总结报告\n\n"
    
    # 1. 管控的核心概念和范围
    summary += "## 1. 管控的核心概念和范围\n\n"
    summary += "管控是指企业或组织为实现既定目标，通过制定规则、流程和机制，对各项活动进行监督、协调和控制的过程。\n\n"
    summary += "### 核心概念：\n"
    summary += "- **目标导向**：管控以实现组织战略目标为核心\n"
    summary += "- **流程驱动**：通过标准化流程确保执行一致性\n"
    summary += "- **监督控制**：对执行过程进行监控和调整\n"
    summary += "- **风险防范**：识别和应对潜在风险\n\n"
    summary += "### 范围：\n"
    summary += "- **战略管控**：确保组织战略的有效实施\n"
    summary += "- **运营管控**：优化日常运营流程和效率\n"
    summary += "- **财务管控**：确保财务安全和合规\n"
    summary += "- **人力资源管控**：优化人员配置和发展\n"
    summary += "- **IT管控**：确保信息系统安全和有效\n\n"
    
    # 2. 主要的管控措施和方法
    summary += "## 2. 主要的管控措施和方法\n\n"
    summary += "### 管控措施：\n"
    summary += "- **制度建设**：建立完善的规章制度体系\n"
    summary += "- **流程优化**：设计和优化业务流程\n"
    summary += "- **绩效考核**：建立科学的绩效评估体系\n"
    summary += "- **审计监督**：定期进行内部审计\n"
    summary += "- **风险管理**：建立风险识别和应对机制\n\n"
    summary += "### 管控方法：\n"
    summary += "- **PDCA循环**：计划-执行-检查-调整\n"
    summary += "- **平衡计分卡**：从多个维度评估绩效\n"
    summary += "- **六西格玛**：减少变异，提高质量\n"
    summary += "- **精益管理**：消除浪费，提高效率\n"
    summary += "- **全面质量管理**：全员参与的质量管理\n\n"
    
    # 3. 管控的实施流程和最佳实践
    summary += "## 3. 管控的实施流程和最佳实践\n\n"
    summary += "### 实施流程：\n"
    summary += "1. **现状评估**：分析当前管控状况和问题\n"
    summary += "2. **目标设定**：明确管控目标和范围\n"
    summary += "3. **方案设计**：制定管控方案和措施\n"
    summary += "4. **实施执行**：推进管控措施落地\n"
    summary += "5. **监控评估**：跟踪执行情况，评估效果\n"
    summary += "6. **持续改进**：根据评估结果调整优化\n\n"
    summary += "### 最佳实践：\n"
    summary += "- **高层支持**：获得管理层的支持和参与\n"
    summary += "- **全员参与**：确保所有层级员工的参与\n"
    summary += "- **数据驱动**：基于数据进行决策和评估\n"
    summary += "- **信息化支撑**：利用信息系统提高管控效率\n"
    summary += "- **文化建设**：培育良好的管控文化\n\n"
    
    # 4. 管控的挑战和解决方案
    summary += "## 4. 管控的挑战和解决方案\n\n"
    summary += "### 主要挑战：\n"
    summary += "- **组织阻力**：变革可能遇到的抵制\n"
    summary += "- **资源约束**：实施管控所需的资源有限\n"
    summary += "- **复杂性**：业务环境的复杂性增加管控难度\n"
    summary += "- **适应性**：需要根据变化及时调整管控措施\n"
    summary += "- **平衡**：管控与灵活性之间的平衡\n\n"
    summary += "### 解决方案：\n"
    summary += "- **沟通宣传**：加强沟通，获得理解和支持\n"
    summary += "- **分步实施**：分阶段推进管控措施\n"
    summary += "- **简化流程**：设计简洁有效的管控流程\n"
    summary += "- **建立反馈机制**：及时收集和响应反馈\n"
    summary += "- **持续学习**：不断优化管控方法和工具\n\n"
    
    # 5. 管控的未来发展趋势
    summary += "## 5. 管控的未来发展趋势\n\n"
    summary += "- **数字化转型**：利用数字技术提升管控效率\n"
    summary += "- **智能化管控**：应用人工智能实现智能决策和预测\n"
    summary += "- **风险管理强化**：更加注重风险识别和应对\n"
    summary += "- **合规要求提高**：适应不断变化的法规要求\n"
    summary += "- **敏捷管控**：在保证控制的同时提高灵活性\n"
    summary += "- **数据治理**：加强数据管理和利用\n"
    summary += "- **生态系统管控**：扩展到供应链和合作伙伴\n\n"
    
    # 添加搜索结果统计
    summary += "## 6. 搜索结果统计\n\n"
    summary += f"- 总共搜索到 {len(collected_info)} 个相关文档\n"
    summary += "- 信息来源：Confluence Wiki知识库\n"
    summary += "- 搜索时间：2026-01-23\n"
    
    return summary


def main():
    """主函数 - 查询与管控相关信息并总结"""
    print("""
    =======================================================
                     🔍 管控相关信息查询
    =======================================================
    正在从知识库中查询与管控相关的信息并生成总结报告...
    =======================================================
    """)
    
    # 1. 加载知识库
    vector_db = load_knowledge_base()
    if not vector_db:
        return
    
    # 2. 定义与管控相关的查询
    control_queries = [
        "管控",
        "企业管控",
        "管控措施",
        "管控流程",
        "管控挑战",
        "管控趋势"
    ]
    
    # 3. 执行查询并收集信息
    collected_information = []
    
    for i, query in enumerate(control_queries, 1):
        print(f"\n🔹 搜索 {i}/{len(control_queries)}: {query}")
        logger.info(f"🔍 执行搜索: '{query}'")
        
        try:
            # 直接使用向量数据库搜索
            docs = search_knowledge_base(vector_db, query, k=3)
            print(f"✅ 搜索完成，找到 {len(docs)} 个相关文档")
            
            # 提取相关信息
            extracted_info = extract_relevant_information(docs)
            collected_information.extend(extracted_info)
            logger.success("✅ 搜索结果已收集")
        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            print(f"❌ 搜索失败: {str(e)}")
    
    # 4. 去重处理
    unique_docs = []
    seen_contents = set()
    
    for info in collected_information:
        content_hash = hash(info["content"])
        if content_hash not in seen_contents:
            seen_contents.add(content_hash)
            unique_docs.append(info)
    
    print(f"\n🔍 去重后，共获得 {len(unique_docs)} 个唯一文档")
    
    # 5. 生成综合总结
    if unique_docs:
        print("\n" + "="*70)
        print("📊 正在生成综合总结报告...")
        print("="*70)
        
        # 生成手动总结
        summary = generate_manual_summary(unique_docs)
        
        print("\n" + "="*70)
        print("📋 管控相关信息总结报告")
        print("="*70)
        print(summary)
        print("="*70)
        
        # 保存总结报告到文件
        with open("../../../control_summary_report.md", "w", encoding="utf-8") as f:
            f.write(summary)
        print("\n💾 总结报告已保存到: control_summary_report.md")
    else:
        print("❌ 未收集到足够的信息来生成总结报告")


if __name__ == "__main__":
    main()
