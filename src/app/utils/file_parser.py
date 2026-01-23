import pdfplumber
import docx
from fastapi import UploadFile
import io
from loguru import logger
from core.error_handler import raise_bad_request, raise_internal_error
import json

# 尝试导入可选依赖
try:
    from PIL import Image
    import pytesseract
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    logger.warning("OCR dependencies not available, image processing will be limited")
    OCR_AVAILABLE = False


async def parse_resume_file(file: UploadFile) -> str:
    """
    解析上传的文件内容为纯文本
    支持: .pdf, .docx, .txt
    """
    if not file.filename:
        raise_bad_request("无效的文件上传，缺少文件名")

    filename = file.filename.lower()
    content_text = ""

    try:
        file_bytes = await file.read()
        file_stream = io.BytesIO(file_bytes)

        if filename.endswith(".pdf"):
            with pdfplumber.open(file_stream) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        content_text += text + "\n"
                # 尝试提取表格
                tables = []
                with pdfplumber.open(file_stream) as pdf:
                    for page in pdf.pages:
                        page_tables = page.extract_tables()
                        if page_tables:
                            tables.extend(page_tables)
                if tables:
                    content_text += "\n=== 表格内容 ===\n"
                    for i, table in enumerate(tables):
                        content_text += f"表格 {i+1}:\n"
                        for row in table:
                            content_text += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"

        elif filename.endswith(".docx"):
            doc = docx.Document(file_stream)
            content_text = "\n".join([para.text for para in doc.paragraphs])

        elif filename.endswith(".txt"):
            content_text = file_bytes.decode("utf-8")

        elif filename.endswith((".jpg", ".jpeg", ".png", ".gif")):
            # 处理图片文件
            content_text = await parse_image_file(file_bytes)

        else:
            raise_bad_request("不支持的文件格式，仅支持 PDF, DOCX, TXT, JPG, JPEG, PNG, GIF")

        if len(content_text.strip()) < 10:
            raise_bad_request("文件内容为空或无法识别")

        return content_text

    except Exception as e:
        logger.error(f"文件解析失败: {e}")
        raise_internal_error(f"文件解析失败: {str(e)}", exc=e)


async def parse_image_file(image_bytes: bytes) -> str:
    """
    解析图片文件，提取文字和图表信息
    """
    if OCR_AVAILABLE and 'Image' in globals() and 'pytesseract' in globals():
        try:
            # 使用PIL打开图片
            image = Image.open(io.BytesIO(image_bytes))
            
            # 使用Tesseract进行OCR
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            
            # 尝试图表识别
            chart_info = ""
            if 'cv2' in globals() and 'np' in globals():
                try:
                    # 转换为OpenCV格式进行图表识别
                    img_array = np.array(image)
                    if len(img_array.shape) == 3:
                        img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    else:
                        img_gray = img_array
                    
                    # 简单的图表识别（检测直线和形状）
                    edges = cv2.Canny(img_gray, 50, 150)
                    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
                    
                    if lines is not None:
                        chart_info = "\n=== 图表检测 ===\n"
                        chart_info += f"检测到 {len(lines)} 条直线，可能包含图表\n"
                except Exception as e:
                    logger.warning(f"Chart detection failed: {e}")
            
            return f"=== 图片OCR结果 ===\n{text}\n{chart_info}"
            
        except Exception as e:
            logger.error(f"图片解析失败: {e}")
            return f"图片解析失败: {str(e)}"
    else:
        return "OCR功能不可用，无法解析图片内容。请安装必要的依赖：pillow、pytesseract、opencv-python"



async def analyze_resume_multimodal(file: UploadFile) -> dict:
    """
    多模态简历分析
    返回包含文本、表格、图表等信息的结构化数据
    """
    if not file.filename:
        raise_bad_request("无效的文件上传，缺少文件名")

    filename = file.filename.lower()
    analysis_result = {
        "text": "",
        "tables": [],
        "charts": [],
        "images": []
    }

    try:
        file_bytes = await file.read()
        file_stream = io.BytesIO(file_bytes)

        if filename.endswith(".pdf"):
            # 提取文本
            with pdfplumber.open(file_stream) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        analysis_result["text"] += text + "\n"
            
            # 提取表格
            with pdfplumber.open(file_stream) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables:
                        analysis_result["tables"].extend(tables)
            
            # 提取图片（PDF中）
            # 这里可以添加PDF图片提取逻辑

        elif filename.endswith((".jpg", ".jpeg", ".png", ".gif")):
            # 处理图片文件
            image_analysis = await parse_image_file(file_bytes)
            analysis_result["text"] = image_analysis
            analysis_result["images"].append("Image content analyzed")

        else:
            # 其他格式使用默认解析
            analysis_result["text"] = await parse_resume_file(file)

        return analysis_result

    except Exception as e:
        logger.error(f"多模态分析失败: {e}")
        raise_internal_error(f"多模态分析失败: {str(e)}", exc=e)
