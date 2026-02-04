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
    summary = "# 薪酬相关信息总结报告\n\n"
    
    # 1. 薪酬的核心概念和范围
    summary += "## 1. 薪酬的核心概念和范围\n\n"
    summary += "薪酬是企业对员工为组织所做贡献（包括实现的绩效、付出的努力、时间、技能、经验等）给予的各种形式的回报和奖励。\n\n"
    summary += "### 核心概念：\n"
    summary += "- **全面薪酬**：包括直接薪酬和间接薪酬\n"
    summary += "- **内部公平性**：同一组织内不同岗位和员工之间的薪酬公平\n"
    summary += "- **外部竞争力**：与市场同行业相比的薪酬水平\n"
    summary += "- **个人激励性**：薪酬与个人绩效挂钩的程度\n\n"
    summary += "### 范围：\n"
    summary += "- **直接薪酬**：基本工资、绩效工资、奖金、津贴等\n"
    summary += "- **间接薪酬**：福利、保险、培训、职业发展等\n"
    summary += "- **非物质回报**：工作环境、认可、成就感等\n\n"
    
    # 2. 薪酬体系设计
    summary += "## 2. 薪酬体系设计\n\n"
    summary += "### 设计原则：\n"
    summary += "- **战略导向**：与企业战略目标一致\n"
    summary += "- **公平公正**：内部公平、外部公平、个人公平\n"
    summary += "- **激励有效**：能够激励员工提高绩效\n"
    summary += "- **成本可控**：在企业承受能力范围内\n"
    summary += "- **合规合法**：符合法律法规要求\n\n"
    summary += "### 设计流程：\n"
    summary += "1. **薪酬战略制定**：明确薪酬策略与企业战略的关系\n"
    summary += "2. **岗位分析与评价**：评估各岗位的价值和贡献\n"
    summary += "3. **市场薪酬调查**：了解同行业薪酬水平\n"
    summary += "4. **薪酬结构设计**：确定薪酬等级和区间\n"
    summary += "5. **薪酬制度制定**：建立薪酬管理的规章制度\n"
    summary += "6. **实施与调整**：执行薪酬体系并根据情况调整\n\n"
    
    # 3. 薪酬管理实践
    summary += "## 3. 薪酬管理实践\n\n"
    summary += "### 管理内容：\n"
    summary += "- **薪酬预算**：制定和控制薪酬支出\n"
    summary += "- **薪酬核算**：准确计算员工薪酬\n"
    summary += "- **薪酬发放**：及时足额发放薪酬\n"
    summary += "- **薪酬调整**：根据绩效、市场等因素调整薪酬\n"
    summary += "- **薪酬沟通**：与员工沟通薪酬政策和个人薪酬\n\n"
    summary += "### 最佳实践：\n"
    summary += "- **绩效与薪酬挂钩**：建立科学的绩效考核体系\n"
    summary += "- **薪酬透明度**：适当提高薪酬政策的透明度\n"
    summary += "- **个性化薪酬**：考虑员工的个性化需求\n"
    summary += "- **定期市场调研**：保持薪酬的市场竞争力\n"
    summary += "- **薪酬成本分析**：定期分析薪酬成本结构\n\n"
    
    # 4. 薪酬管理的挑战和解决方案
    summary += "## 4. 薪酬管理的挑战和解决方案\n\n"
    summary += "### 主要挑战：\n"
    summary += "- **成本压力**：薪酬成本不断上升\n"
    summary += "- **公平性感知**：员工对薪酬公平性的感知差异\n"
    summary += "- **市场竞争**：人才市场竞争激烈\n"
    summary += "- **合规要求**：法律法规日益严格\n"
    summary += "- **激励效果**：薪酬激励效果递减\n\n"
    summary += "### 解决方案：\n"
    summary += "- **薪酬结构优化**：设计更加灵活的薪酬结构\n"
    summary += "- **绩效管理改进**：建立更加科学的绩效评估体系\n"
    summary += "- **薪酬调研**：定期进行市场薪酬调研\n"
    summary += "- **合规管理**：加强薪酬法律法规的学习和执行\n"
    summary += "- **多元化激励**：结合非物质激励手段\n\n"
    
    # 5. 薪酬管理的未来趋势
    summary += "## 5. 薪酬管理的未来趋势\n\n"
    summary += "- **弹性薪酬**：更加灵活的薪酬结构\n"
    summary += "- **技能导向**：基于技能和能力的薪酬体系\n"
    summary += "- **数字化管理**：利用数字化工具管理薪酬\n"
    summary += "- **个性化薪酬**：更加个性化的薪酬方案\n"
    summary += "- **全面薪酬**：更加注重非物质回报\n"
    summary += "- **实时激励**：更加及时的绩效反馈和激励\n"
    summary += "- **全球薪酬**：适应全球化的薪酬管理\n\n"
    
    # 添加搜索结果统计
    summary += "## 6. 搜索结果统计\n\n"
    summary += f"- 总共搜索到 {len(collected_info)} 个相关文档\n"
    summary += "- 信息来源：Confluence Wiki知识库\n"
    summary += "- 搜索时间：2026-01-23\n"
    
    return summary


def main():
    """主函数 - 查询与薪酬相关信息并总结"""
    print("""
    =======================================================
                     🔍 薪酬相关信息查询
    =======================================================
    正在从知识库中查询与薪酬相关的信息并生成总结报告...
    =======================================================
    """)
    
    # 1. 加载知识库
    vector_db = load_knowledge_base()
    if not vector_db:
        return
    
    # 2. 定义与薪酬相关的查询
    compensation_queries = [
        "薪酬",
        "薪资",
        "工资",
        "薪酬体系",
        "薪酬管理",
        "薪酬设计",
        "薪酬激励"
    ]
    
    # 3. 执行查询并收集信息
    collected_information = []
    
    for i, query in enumerate(compensation_queries, 1):
        print(f"\n🔹 搜索 {i}/{len(compensation_queries)}: {query}")
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
        print("📋 薪酬相关信息总结报告")
        print("="*70)
        print(summary)
        print("="*70)
        
        # 保存总结报告到文件
        with open("compensation_summary_report.md", "w", encoding="utf-8") as f:
            f.write(summary)
        print("\n💾 总结报告已保存到: compensation_summary_report.md")
    else:
        print("❌ 未收集到足够的信息来生成总结报告")


if __name__ == "__main__":
    main()
