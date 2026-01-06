import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger

router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "blog_data")
GRAPH_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_graph_cache.json")


class KnowledgeNode(BaseModel):
    id: str
    label: str
    type: str
    importance: float
    metadata: Optional[dict] = None


class KnowledgeEdge(BaseModel):
    source: str
    target: str
    relationship: str
    weight: float


class KnowledgeGraphData(BaseModel):
    nodes: List[KnowledgeNode]
    edges: List[KnowledgeEdge]


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """从文本中提取关键词"""
    import re
    words = re.findall(r'\b[a-zA-Z\u4e00-\u9fff]{2,}\b', text.lower())
    stopwords = {'的', '了', '是', '在', '和', '与', '或', '等', '对于', '关于', '这个', '那个', '这些', 'those', 'this', 'that', 'the', 'and', 'or', 'is', 'are'}
    filtered = [w for w in words if w not in stopwords]
    from collections import Counter
    word_counts = Counter(filtered)
    return [word for word, _ in word_counts.most_common(max_keywords)]


def generate_knowledge_graph() -> KnowledgeGraphData:
    """生成知识图谱数据"""
    nodes = []
    edges = []
    node_map = {}

    json_files = []
    if os.path.exists(DATA_DIR):
        for filename in os.listdir(DATA_DIR):
            if filename.endswith('.json'):
                json_files.append(os.path.join(DATA_DIR, filename))

    all_keywords = {}
    doc_count = 0

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                posts = data if isinstance(data, list) else [data]

            for post in posts:
                doc_count += 1
                title = post.get('title', 'Untitled')
                content = post.get('content', '')
                tags = post.get('tags', '')

                doc_id = f"doc_{doc_count}"
                doc_node = KnowledgeNode(
                    id=doc_id,
                    label=title[:30] + ('...' if len(title) > 30 else ''),
                    type="document",
                    importance=0.8,
                    metadata={"source": file_path, "tags": tags}
                )
                nodes.append(doc_node)
                node_map[doc_id] = doc_node

                if isinstance(tags, str):
                    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
                    for tag in tag_list:
                        if tag not in node_map:
                            tag_node = KnowledgeNode(
                                id=f"tag_{tag}",
                                label=tag,
                                type="keyword",
                                importance=0.5
                            )
                            nodes.append(tag_node)
                            node_map[f"tag_{tag}"] = tag_node

                        edges.append(KnowledgeEdge(
                            source=doc_id,
                            target=f"tag_{tag}",
                            relationship="has_tag",
                            weight=1.0
                        ))

                keywords = extract_keywords(content + ' ' + title)
                for i, keyword in enumerate(keywords[:5]):
                    all_keywords[keyword] = all_keywords.get(keyword, 0) + 1

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")

    for keyword, count in all_keywords.items():
        if count >= 2 and keyword not in node_map:
            keyword_node = KnowledgeNode(
                id=f"kw_{keyword}",
                label=keyword,
                type="concept",
                importance=min(0.9, 0.3 + count * 0.1)
            )
            nodes.append(keyword_node)

    for doc in nodes:
        if doc.type == "document":
            doc_keywords = []
            try:
                with open(doc.metadata["source"], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for post in data:
                        if post.get('title') in doc.label:
                            doc_keywords = extract_keywords(post.get('content', '') + ' ' + post.get('title', ''))
                            break
            except:
                pass

            for keyword in doc_keywords[:3]:
                kw_id = f"kw_{keyword}"
                if kw_id in node_map:
                    edges.append(KnowledgeEdge(
                        source=doc.id,
                        target=kw_id,
                        relationship="contains",
                        weight=0.6
                    ))

    top_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_keywords:
        category_node = KnowledgeNode(
            id="main_category",
            label="核心主题",
            type="category",
            importance=1.0
        )
        nodes.append(category_node)

        for keyword, _ in top_keywords:
            kw_id = f"kw_{keyword}"
            if kw_id in node_map:
                edges.append(KnowledgeEdge(
                    source="main_category",
                    target=kw_id,
                    relationship="includes",
                    weight=0.8
                ))

    return KnowledgeGraphData(nodes=nodes, edges=edges)


@router.get("/graph", response_model=KnowledgeGraphData)
async def get_knowledge_graph():
    """获取知识图谱数据"""
    try:
        if os.path.exists(GRAPH_CACHE_FILE):
            file_mtime = os.path.getmtime(GRAPH_CACHE_FILE)
            cache_age = (os.path.getsize(GRAPH_CACHE_FILE) > 100)

            if cache_age:
                with open(GRAPH_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    return KnowledgeGraphData(**cache_data)

        graph_data = generate_knowledge_graph()

        try:
            with open(GRAPH_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "nodes": [n.model_dump() for n in graph_data.nodes],
                    "edges": [e.model_dump() for e in graph_data.edges]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache graph data: {e}")

        return graph_data
    except Exception as e:
        logger.error(f"Failed to generate knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/refresh")
async def refresh_knowledge_graph():
    """刷新知识图谱缓存"""
    try:
        graph_data = generate_knowledge_graph()

        with open(GRAPH_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "nodes": [n.model_dump() for n in graph_data.nodes],
                "edges": [e.model_dump() for e in graph_data.edges]
            }, f, ensure_ascii=False, indent=2)

        return {"status": "success", "message": "Knowledge graph refreshed"}
    except Exception as e:
        logger.error(f"Failed to refresh knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/stats")
async def get_graph_stats():
    """获取知识图谱统计信息"""
    try:
        graph_data = generate_knowledge_graph()

        node_types = {}
        for node in graph_data.nodes:
            node_types[node.type] = node_types.get(node.type, 0) + 1

        return {
            "total_nodes": len(graph_data.nodes),
            "total_edges": len(graph_data.edges),
            "node_types": node_types,
            "average_connections": round(len(graph_data.edges) / max(len(graph_data.nodes), 1), 2)
        }
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
