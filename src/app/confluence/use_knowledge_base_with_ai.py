import os
import sys

# 设置HuggingFace国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from loguru import logger

# 配置路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_DIR = os.path.join(CURRENT_DIR, "confluence_faiss_index")

# 系统提示词模板
SYSTEM_PROMPT = """
你是一个专业的知识库助手，请根据提供的上下文信息回答用户的问题。

上下文信息：
{context}

请严格基于以上上下文回答用户问题，不要添加任何外部信息或猜测。如果上下文信息不足以回答问题，请明确说明。
"""


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


def create_qa_chain(vector_db):
    """创建基于知识库的问答链"""
    logger.info("🤖 正在初始化AI助手...")
    
    try:
        # 初始化语言模型
        llm = HuggingFaceEndpoint(
            repo_id="mistralai/Mistral-7B-Instruct-v0.3",
            task="text-generation",
            max_new_tokens=512,
            temperature=0.1,
        )
        
        # 创建检索器
        retriever = vector_db.as_retriever(k=3)
        
        # 创建提示词模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{question}")
        ])
        
        # 创建输出解析器
        output_parser = StrOutputParser()
        
        # 构建RAG链 - 使用更兼容Python 3.9的方式
        def rag_chain(question):
            # 1. 检索相关文档
            docs = retriever.invoke(question)
            
            # 2. 处理文档内容
            context = "\n".join(doc.page_content for doc in docs)
            
            # 3. 格式化提示词
            formatted_prompt = prompt.format(context=context, question=question)
            
            # 4. 调用语言模型
            response = llm.invoke(formatted_prompt)
            
            # 5. 解析输出
            parsed_response = output_parser.invoke(response)
            
            return parsed_response
        
        logger.success("✅ AI助手初始化完成！")
        return rag_chain
    except Exception as e:
        logger.error(f"❌ AI助手初始化失败: {e}")
        return None


def main():
    """主函数 - 演示如何在与AI对话时使用知识库"""
    print("""
    =======================================================
                     🧠 知识库AI对话演示
    =======================================================
    这是一个基于Confluence Wiki知识库的智能对话系统示例
    你可以提出与知识库内容相关的问题，AI将基于知识库回答
    输入 'exit' 或 'quit' 退出对话
    =======================================================
    """)
    
    # 1. 加载知识库
    vector_db = load_knowledge_base()
    if not vector_db:
        return
    
    # 2. 创建问答链
    qa_chain = create_qa_chain(vector_db)
    if not qa_chain:
        return
    
    # 3. 开始对话
    print("\n💡 系统提示：你可以尝试提问关于HCM Cloud、PaaS平台、数字化企业等相关问题")
    print("\n🤖 AI：你好！有什么我可以帮你解答的问题吗？")
    
    while True:
        try:
            # 获取用户输入
            user_input = input("👤 用户：").strip()
            
            if not user_input:
                continue
            
            # 退出条件
            if user_input.lower() in ['exit', 'quit', '退出', '结束']:
                print("🤖 AI：再见！")
                break
            
            # 4. 使用知识库和AI生成回答
            logger.info(f"🔍 用户查询: '{user_input}'")
            response = qa_chain.invoke(user_input)
            
            print("🤖 AI：" + response)
            logger.success("✅ 回答生成完成")
            
        except KeyboardInterrupt:
            print("\n🤖 AI：再见！")
            break
        except Exception as e:
            logger.error(f"❌ 回答生成失败: {e}")
            print(f"🤖 AI：对不起，我在处理你的问题时遇到了错误。错误信息：{str(e)}")


if __name__ == "__main__":
    main()
