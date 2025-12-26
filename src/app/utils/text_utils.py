def clean_json_output(text: str) -> str:
    """
    清洗 LLM 输出的 JSON 字符串，去除常见的 Markdown 代码块标记。
    """
    text = text.strip()
    # 移除 ```json 和 结尾的 ```
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]

    return text.strip()
