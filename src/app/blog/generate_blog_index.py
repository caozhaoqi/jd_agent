import os
import json
import frontmatter
import re

# === 配置路径 ===
# 你的博客文章源码目录
SOURCE_DIR = "/Users/caozhaoqi/Downloads/hexo-bamboo-blog/source/_posts"
# 输出文件路径
OUTPUT_FILE = "blog_data.json"


def clean_markdown(text):
    """
    清洗 Markdown 标记，只保留纯文本，方便 AI 检索
    """
    # 去除代码块 ```...```
    text = re.sub(r'```[\s\S]*?```', '', text)
    # 去除图片 ![...](...)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # 去除链接 [ ... ](...)，只保留文本
    text = re.sub(r'\[([^\]]+)\]\(.*?\)', r'\1', text)
    # 去除标题符号 #
    text = re.sub(r'#+\s', '', text)
    # 去除加粗/斜体 * 或 _
    text = re.sub(r'[*_]{1,2}(.*?)[*_]{1,2}', r'\1', text)
    # 去除多余换行
    text = re.sub(r'\n+', '\n', text).strip()
    return text


def generate_index():
    posts = []

    if not os.path.exists(SOURCE_DIR):
        print(f"❌ 错误：路径不存在 -> {SOURCE_DIR}")
        return

    print(f"📂 正在扫描目录: {SOURCE_DIR} ...")

    # 遍历目录 (包括子目录)
    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)

                try:
                    # 加载并解析 Markdown
                    with open(file_path, "r", encoding="utf-8") as f:
                        post = frontmatter.load(f)

                    # 提取元数据 (Front Matter)
                    title = post.metadata.get("title", file.replace(".md", ""))
                    date = str(post.metadata.get("date", ""))
                    tags = post.metadata.get("tags", [])
                    categories = post.metadata.get("categories", [])

                    # 确保 tags/categories 是列表
                    if isinstance(tags, str): tags = [tags]
                    if isinstance(categories, str): categories = [categories]

                    # 清洗正文
                    content = clean_markdown(post.content)

                    # 如果内容太短，可能是空文章，跳过
                    if len(content) < 50:
                        continue

                    # 构造数据结构
                    post_data = {
                        "source": file,  # 文件名作为来源标识
                        "title": title,
                        "date": date,
                        "tags": tags,
                        "categories": categories,
                        "content": content,
                        "url": f"/posts/{title}/"  # 假设的 URL 结构
                    }

                    posts.append(post_data)
                    print(f"✅ 已处理: {title}")

                except Exception as e:
                    print(f"⚠️ 解析失败: {file} - {str(e)}")

    # 保存为 JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 完成！共处理 {len(posts)} 篇文章。")
    print(f"📁 数据已保存至: {os.path.abspath(OUTPUT_FILE)}")


if __name__ == "__main__":
    generate_index()