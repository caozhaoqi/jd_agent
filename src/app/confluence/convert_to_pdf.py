import os
import json
import requests
import pdfkit
from bs4 import BeautifulSoup
from utils.logger import logger

# 配置路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
DATA_DIR = os.path.join(PROJECT_ROOT, "confluence_data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "confluence_pdf_documents")
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)


def download_image(url, page_id, image_index):
    """下载图片并保存到本地"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # 检查Content-Type是否为图片
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                logger.warning(
                    f"⚠️  不是图片类型，跳过: {url} (Content-Type: {content_type})"
                )
                return None

            # 生成图片文件名
            image_ext = (
                content_type.split("/")[-1] if content_type else url.split(".")[-1]
            )
            if image_ext in ["png", "jpg", "jpeg", "gif", "bmp"]:
                pass
            else:
                image_ext = "png"  # 默认使用png格式
            image_filename = f"page_{page_id}_image_{image_index}.{image_ext}"
            image_path = os.path.join(IMAGE_DIR, image_filename)

            # 保存图片
            with open(image_path, "wb") as f:
                f.write(response.content)

            logger.info(f"✅ 下载图片成功: {image_filename}")
            return image_path
    except Exception as e:
        logger.error(f"❌ 下载图片失败 {url}: {str(e)}")
    return None


def convert_confluence_html_to_pdf(html_content, pdf_path, page_info):
    """将Confluence HTML内容转换为PDF"""
    soup = BeautifulSoup(html_content, "html.parser")

    # 处理图片 - 支持标准img标签和Confluence特有ac:image标签
    # 先处理标准img标签
    images = soup.find_all("img")
    for i, img in enumerate(images):
        img_url = img.get("src")
        if img_url:
            # 下载图片
            image_path = download_image(img_url, page_info["page_id"], i)
            if image_path:
                # 替换HTML中的图片URL为本地路径
                img["src"] = image_path

    # 处理Confluence特有ac:image标签
    ac_images = soup.find_all("ac:image")
    for i, ac_img in enumerate(ac_images):
        # 获取附件文件名
        ri_attachment = ac_img.find("ri:attachment")
        if ri_attachment:
            filename = ri_attachment.get("ri:filename")
            if filename:
                # 构建图片URL (Confluence附件URL格式)
                img_url = f"https://wiki.hcmcloud.cn/download/attachments/{page_info['page_id']}/{filename}"
                # 下载图片
                image_path = download_image(
                    img_url, page_info["page_id"], len(images) + i
                )
                if image_path:
                    # 创建新的img标签替换ac:image
                    new_img = soup.new_tag("img")
                    new_img["src"] = image_path
                    new_img["width"] = "800"
                    ac_img.replace_with(new_img)

    # 创建完整的HTML内容
    full_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{page_info['title']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            h1 {{ color: #333; }}
            h2 {{ color: #555; }}
            h3 {{ color: #777; }}
            p {{ line-height: 1.6; }}
            img {{ max-width: 100%; height: auto; }}
            .page-info {{ background-color: #f5f5f5; padding: 10px; margin-bottom: 20px; }}
            .separator {{ border-top: 1px solid #ddd; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="page-info">
            <h1>{page_info['title']}</h1>
            <p>URL: {page_info['url']}</p>
            <p>作者: {page_info['author']}</p>
            <p>创建时间: {page_info['created_at']}</p>
            <p>更新时间: {page_info['updated_at']}</p>
        </div>
        <div class="separator"></div>
        {str(soup)}
    </body>
    </html>
    """

    try:
        # 配置pdfkit
        options = {
            "page-size": "A4",
            "margin-top": "20mm",
            "margin-right": "20mm",
            "margin-bottom": "20mm",
            "margin-left": "20mm",
            "encoding": "UTF-8",
            "no-outline": None,
            "quiet": "",
            "load-error-handling": "ignore",
            "load-media-error-handling": "ignore",
        }

        # 转换HTML为PDF
        pdfkit.from_string(full_html, pdf_path, options=options)
        logger.info(f"✅ 转换PDF成功: {pdf_path}")
        return True
    except Exception as e:
        logger.error(f"❌ 转换PDF失败 {pdf_path}: {str(e)}")
        return False


def convert_confluence_pages_to_pdf():
    """将Confluence页面数据转换为PDF文档"""
    logger.info("🚀 开始将Confluence页面转换为PDF文档...")

    # 读取页面数据
    pages_file = os.path.join(DATA_DIR, "confluence_pages.json")
    if not os.path.exists(pages_file):
        logger.error("❌ 未找到Confluence页面数据文件")
        return

    with open(pages_file, "r", encoding="utf-8") as f:
        pages = json.load(f)

    logger.info(f"✅ 成功加载 {len(pages)} 个页面数据")

    # 转换每个页面
    success_count = 0
    for i, page in enumerate(pages, 1):
        logger.info(f"🔄 正在转换页面 {i}/{len(pages)}: {page['title']}")

        # 生成PDF文件名
        pdf_filename = f"{page['title']}.pdf".replace("/", "_").replace("\\", "_")
        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)

        # 转换内容
        if page["content"]:
            if convert_confluence_html_to_pdf(page["content"], pdf_path, page):
                success_count += 1
        else:
            logger.warning(f"⚠️  页面 {page['title']} 没有内容，跳过转换")

    logger.info(
        f"🎉 所有页面转换完成！成功转换 {success_count}/{len(pages)} 个页面，PDF文档保存在: {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    convert_confluence_pages_to_pdf()
