import os
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager

# 设置HuggingFace国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from loguru import logger

# 配置路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
INDEX_DIR = os.path.join(PROJECT_ROOT, "confluence_faiss_index")

# 全局变量存储知识库实例
vector_db = None

def load_knowledge_base():
    """加载知识库向量数据库"""
    global vector_db
    
    if vector_db is not None:
        return vector_db
    
    logger.info("📚 正在加载知识库向量数据库...")
    
    try:
        # 初始化Embedding模型（与构建索引时使用相同的模型）
        embedding_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        
        # 加载FAISS向量数据库
        if not os.path.exists(INDEX_DIR):
            logger.warning(f"⚠️ 知识库索引目录不存在: {INDEX_DIR}")
            return None
            
        vector_db = FAISS.load_local(
            INDEX_DIR,
            embedding_model,
            allow_dangerous_deserialization=True
        )
        logger.success("✅ 知识库加载成功！")
        return vector_db
    except Exception as e:
        logger.error(f"❌ 知识库加载失败: {e}")
        # 不抛出异常，允许应用启动，但在查询时报错
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        load_knowledge_base()
        logger.success("✅ 应用启动成功，知识库加载尝试完成")
    except Exception as e:
        logger.error(f"❌ 应用启动初始化失败: {e}")
    yield
    # 关闭时的清理工作（如果有）

# 初始化FastAPI应用
app = FastAPI(
    title="知识库通用查询API",
    description="通过API或UI界面查询Confluence Wiki知识库",
    version="1.0.0",
    lifespan=lifespan
)

# 初始化模板引擎
templates = Jinja2Templates(directory=".")

# 请求模型
class QueryRequest(BaseModel):
    query: str
    k: int = 3

# 响应模型
class QueryResponse(BaseModel):
    query: str
    results: list
    total: int


def search_knowledge_base(query: str, k: int = 3):
    """在知识库中搜索相关文档"""
    try:
        db = load_knowledge_base()
        if db is None:
             raise HTTPException(status_code=503, detail="知识库未加载或不存在，请先构建知识库索引")

        # 使用向量数据库的相似性搜索功能
        results = db.similarity_search(
            query=query,
            k=k
        )
        
        # 格式化搜索结果
        formatted_results = []
        for i, doc in enumerate(results, 1):
            formatted_results.append({
                "id": i,
                "content": doc.page_content[:500] + ("..." if len(doc.page_content) > 500 else ""),
                "metadata": doc.metadata
            })
        
        return formatted_results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """根路径，返回UI界面"""
    return templates.TemplateResponse(
        "knowledge_query_ui.html",
        {"request": request}
    )


@app.post("/api/query", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest):
    """API接口：查询知识库"""
    try:
        results = search_knowledge_base(request.query, request.k)
        return QueryResponse(
            query=request.query,
            results=results,
            total=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    try:
        db = load_knowledge_base()
        if db is None:
            return {"status": "unhealthy", "message": "知识库未加载"}
        return {"status": "healthy", "message": "知识库服务运行正常"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


# 创建UI界面HTML文件
def create_ui_template():
    """创建UI界面模板文件"""
    ui_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>知识库通用查询</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: '#3b82f6',
                        secondary: '#64748b',
                        success: '#10b981',
                        warning: '#f59e0b',
                        danger: '#ef4444',
                        dark: '#1e293b',
                        light: '#f8fafc'
                    },
                    fontFamily: {
                        sans: ['Inter', 'system-ui', 'sans-serif'],
                    },
                },
            }
        }
    </script>
    <style type="text/tailwindcss">
        @layer utilities {
            .content-auto {
                content-visibility: auto;
            }
            .glass {
                background: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
        }
    </style>
</head>
<body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <!-- 头部 -->
        <header class="text-center mb-8">
            <div class="inline-flex items-center justify-center p-2 bg-primary rounded-full mb-4">
                <i class="fa fa-search text-white text-2xl"></i>
            </div>
            <h1 class="text-3xl font-bold text-dark mb-2">知识库通用查询</h1>
            <p class="text-secondary">通过API或UI界面查询Confluence Wiki知识库内容</p>
        </header>

        <!-- 查询表单 -->
        <div class="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-6 mb-8">
            <form id="queryForm" class="space-y-4">
                <div>
                    <label for="query" class="block text-sm font-medium text-gray-700 mb-1">查询内容</label>
                    <input 
                        type="text" 
                        id="query" 
                        name="query" 
                        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary transition-colors"
                        placeholder="请输入查询内容，例如：管控、薪酬、绩效..."
                        required
                    >
                </div>
                <div>
                    <label for="k" class="block text-sm font-medium text-gray-700 mb-1">返回结果数量</label>
                    <select 
                        id="k" 
                        name="k" 
                        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary transition-colors"
                    >
                        <option value="1">1</option>
                        <option value="3" selected>3</option>
                        <option value="5">5</option>
                        <option value="10">10</option>
                    </select>
                </div>
                <button 
                    type="submit" 
                    class="w-full bg-primary hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center"
                >
                    <i class="fa fa-search mr-2"></i> 开始查询
                </button>
            </form>
        </div>

        <!-- 结果区域 -->
        <div class="max-w-4xl mx-auto">
            <div id="loading" class="hidden text-center py-8">
                <div class="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
                <p class="mt-4 text-secondary">正在查询知识库...</p>
            </div>

            <div id="error" class="hidden bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                <div class="flex items-center">
                    <i class="fa fa-exclamation-circle text-red-500 mr-2"></i>
                    <p id="errorMessage" class="text-red-600"></p>
                </div>
            </div>

            <div id="results" class="space-y-4"></div>
        </div>

        <!-- API文档链接 -->
        <footer class="mt-12 text-center text-secondary text-sm">
            <p>API文档：<a href="/docs" class="text-primary hover:underline" target="_blank">/docs</a></p>
            <p class="mt-2">健康检查：<a href="/api/health" class="text-primary hover:underline" target="_blank">/api/health</a></p>
        </footer>
    </div>

    <script>
        // 表单提交处理
        document.getElementById('queryForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const query = document.getElementById('query').value;
            const k = parseInt(document.getElementById('k').value);
            
            // 显示加载状态
            document.getElementById('loading').classList.remove('hidden');
            document.getElementById('error').classList.add('hidden');
            document.getElementById('results').innerHTML = '';
            
            try {
                // 发送API请求
                const response = await fetch('/api/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ query, k })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || '查询失败');
                }
                
                const data = await response.json();
                
                // 显示结果
                displayResults(data);
            } catch (error) {
                document.getElementById('errorMessage').textContent = error.message;
                document.getElementById('error').classList.remove('hidden');
            } finally {
                document.getElementById('loading').classList.add('hidden');
            }
        });

        // 显示结果
        function displayResults(data) {
            const resultsContainer = document.getElementById('results');
            
            if (data.total === 0) {
                resultsContainer.innerHTML = `
                    <div class="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                        <i class="fa fa-info-circle text-gray-400 text-3xl mb-2"></i>
                        <p class="text-gray-600">未找到相关结果</p>
                    </div>
                `;
                return;
            }
            
            const resultsHtml = data.results.map((result, index) => `
                <div class="bg-white rounded-lg shadow-md p-5 hover:shadow-lg transition-shadow">
                    <div class="flex items-center mb-3">
                        <div class="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                            <span class="text-primary font-medium">${index + 1}</span>
                        </div>
                        <h3 class="ml-3 text-lg font-medium text-dark">结果 ${index + 1}</h3>
                    </div>
                    <div class="prose max-w-none">
                        <p class="text-gray-700 mb-3">${result.content}</p>
                    </div>
                    ${result.metadata && Object.keys(result.metadata).length > 0 ? `
                        <div class="mt-3 pt-3 border-t border-gray-100">
                            <h4 class="text-sm font-medium text-gray-500 mb-2">元数据</h4>
                            <div class="text-xs text-gray-600 space-y-1">
                                ${Object.entries(result.metadata).map(([key, value]) => `
                                    <div><span class="font-medium">${key}:</span> ${value}</div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
            `).join('');
            
            resultsContainer.innerHTML = resultsHtml;
        }
    </script>
</body>
</html>
"""
    
    # 写入UI模板文件
    with open("knowledge_query_ui.html", "w", encoding="utf-8") as f:
        f.write(ui_html)
    logger.success("✅ UI模板文件创建成功")


def main():
    """主函数"""
    # 创建UI模板文件
    create_ui_template()
    
    # 启动服务器
    logger.info("🚀 启动知识库通用查询API服务...")
    logger.info("📡 API地址: http://localhost:8000")
    logger.info("📖 API文档: http://localhost:8000/docs")
    logger.info("🖥️ UI界面: http://localhost:8000")
    
    uvicorn.run(
        "generic_knowledge_query:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )


if __name__ == "__main__":
    main()
