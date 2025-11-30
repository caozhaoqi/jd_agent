from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from datasets import Dataset

# 准备测试数据 (Golden Dataset)
data = {
    'question': ['什么是 RAG？', 'Vue3 的生命周期有哪些？'],
    'answer': ['RAG 是检索增强生成...', 'Vue3 生命周期包括...'], # 你的 Agent 生成的答案
    'contexts': [['RAG 技术原理文档...'], ['Vue3 官方文档片段...']], # 你的 Agent 检索到的片段
    'ground_truth': ['RAG 全称 Retrieval-Augmented Generation...', 'setup, onMounted...'] # 人工写的标准答案
}

dataset = Dataset.from_dict(data)

# 开始评估
results = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy, context_precision],
)

print(results)
# 输出: {'faithfulness': 0.89, 'answer_relevancy': 0.92, ...}