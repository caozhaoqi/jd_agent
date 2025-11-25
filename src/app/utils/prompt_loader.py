import yaml
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

# 假设 prompts 文件夹在项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROMPT_DIR = BASE_DIR / "prompts"


def load_prompt(filename: str) -> ChatPromptTemplate:
    """从 YAML 文件加载 Prompt"""
    file_path = PROMPT_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 返回 LangChain 的 Prompt 模板对象
    return ChatPromptTemplate.from_template(config["template"])