import pdfplumber
import docx
from fastapi import UploadFile, HTTPException
import io

from loguru import logger


async def parse_resume_file(file: UploadFile) -> str:
    """
    解析上传的文件内容为纯文本
    支持: .pdf, .docx, .txt
    """
    filename = file.filename.lower()
    content_text = ""

    try:
        # 读取文件二进制内容
        file_bytes = await file.read()
        file_stream = io.BytesIO(file_bytes)

        if filename.endswith(".pdf"):
            with pdfplumber.open(file_stream) as pdf:
                for page in pdf.pages:
                    # 提取文本，过滤空行
                    text = page.extract_text()
                    if text:
                        content_text += text + "\n"

        elif filename.endswith(".docx"):
            doc = docx.Document(file_stream)
            content_text = "\n".join([para.text for para in doc.paragraphs])

        elif filename.endswith(".txt"):
            content_text = file_bytes.decode("utf-8")

        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式，仅支持 PDF, DOCX, TXT")

        if len(content_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="文件内容为空或无法识别")

        return content_text

    except Exception as e:
        logger.debug(f"❌ 解析文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")