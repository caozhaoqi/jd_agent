from flask import Flask, request, Response, stream_with_context
from app.core.rag_engine import rag_engine
import json
import time

app = Flask(__name__)


# 模拟数据库连接 (这里只展示逻辑)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:pass@localhost/db'
# db = SQLAlchemy(app)

@app.route('/api/v1/flask/analyze', methods=['POST'])
def analyze_jd_flask():
    """
    JD要求的 Flask 路由设计与请求处理
    """
    data = request.json
    jd_text = data.get('jd_text', '')

    # 1. 演示 RAG：先从向量库找有没有类似的历史经验
    related_info = rag_engine.search(query=jd_text, top_k=1)
    print(f"RAG 检索结果: {related_info}")

    # 2. 演示 SSE (服务器推送事件)
    @stream_with_context
    def generate():
        # 模拟大模型流式输出
        yield f"data: [Flask] 正在分析 JD...\n\n"
        time.sleep(1)

        if related_info:
            yield f"data: [RAG] 发现库中有相似岗位的面试经验...\n\n"

        yield f"data: [Result] 分析完成，建议重点复习 BGE 和 Flask。\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    # JD要求: 熟悉 Gunicorn (生产环境部署命令: gunicorn -w 4 server_flask:app)
    app.run(debug=True, port=5000)