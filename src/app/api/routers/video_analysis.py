import os
import logging
import shutil
import zipfile
from fastapi import APIRouter, UploadFile, File, Form
from typing import Dict, Any
import tempfile

from app.utils.video_utils import extract_audio_from_video, list_video_files
from openai import OpenAI
from app.core.config import settings
from app.core.error_handler import (
    raise_not_found,
    raise_bad_request,
    raise_internal_error,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def get_openai_client():
    """
    获取OpenAI客户端
    """
    return OpenAI(
        api_key=settings.AUDIO_API_KEY or settings.OPENAI_API_KEY,
        base_url=settings.AUDIO_API_BASE or settings.OPENAI_API_BASE,
    )


def transcribe_audio_file(audio_path: str) -> str:
    """
    转录音频文件为文字
    """
    client = get_openai_client()

    try:
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=settings.ASR_MODEL, file=audio_file, temperature=0.0
            )
        return transcript.text
    except Exception as e:
        logger.error(f"音频转录失败: {e}")
        raise RuntimeError(f"音频转录失败: {e}")


def analyze_key_knowledge(text: str) -> Dict[str, Any]:
    """
    分析文字内容，提取关键知识点
    """
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE)

    try:
        response = client.chat.completions.create(
            model=settings.MODEL_NAME or "gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的课程分析助手，请从以下课程文字内容中提取关键知识点，按照层级结构组织，并对每个知识点进行简要说明。输出格式为JSON，包含knowledge_points（知识点列表）和summary（总结）。每个知识点应包含title（标题）、description（描述）和level（层级，1-3）。",
                },
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )

        import json

        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"知识点分析失败: {e}")
        raise RuntimeError(f"知识点分析失败: {e}")


def generate_visual_summary(knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成可视化总结数据结构
    """
    return {"type": "mind_map", "title": "课程知识点总结", "data": knowledge_data}


def process_video_file(video_path: str) -> Dict[str, Any]:
    """
    处理单个视频文件的核心逻辑
    """
    try:
        audio_path = extract_audio_from_video(video_path)
        transcript_text = transcribe_audio_file(audio_path)
        knowledge_data = analyze_key_knowledge(transcript_text)
        visual_summary = generate_visual_summary(knowledge_data)

        if os.path.exists(audio_path):
            os.remove(audio_path)

        return {
            "video_path": video_path,
            "transcript": transcript_text,
            "knowledge_points": knowledge_data,
            "visual_summary": visual_summary,
        }
    except Exception as e:
        logger.error(f"处理视频文件失败 {video_path}: {e}")
        return {"video_path": video_path, "error": str(e)}


def _analyze_directory_content(directory_path: str) -> Dict[str, Any]:
    """
    分析目录内容的核心逻辑
    """
    video_files = list_video_files(directory_path)
    if not video_files:
        raise_not_found("目录中没有找到视频文件")

    results = [process_video_file(video_path) for video_path in video_files]

    return {
        "directory": directory_path,
        "total_videos": len(video_files),
        "processed_videos": len([r for r in results if "error" not in r]),
        "results": results,
    }


@router.post("/analyze-directory")
async def analyze_video_directory(directory_path: str = Form(...)):
    """
    分析指定目录下的所有视频文件
    """
    if not os.path.exists(directory_path):
        raise_not_found("目录不存在")

    if not os.path.isdir(directory_path):
        raise_bad_request("提供的路径不是一个有效的目录")

    try:
        return _analyze_directory_content(directory_path)
    except Exception as e:
        logger.error(f"分析视频目录失败: {e}")
        raise_internal_error("分析视频目录失败", exc=e)


@router.post("/analyze-zip")
async def analyze_video_zip(file: UploadFile = File(...)):
    """
    上传ZIP文件包含视频项目，解压并分析
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise_bad_request("仅支持ZIP压缩文件")

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, file.filename)

    try:
        with open(zip_path, "wb") as f:
            f.write(await file.read())

        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        result = _analyze_directory_content(extract_dir)

        for item in result.get("results", []):
            if "video_path" in item:
                item["video_path"] = os.path.relpath(item["video_path"], extract_dir)

        result["directory"] = file.filename
        return result

    except Exception as e:
        logger.error(f"分析ZIP文件失败: {e}")
        raise_internal_error("分析ZIP文件失败", exc=e)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/analyze-video")
async def analyze_single_video(file: UploadFile = File(...)):
    """
    分析单个视频文件
    """
    temp_dir = tempfile.gettempdir()
    temp_video_path = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_video_path, "wb") as f:
            f.write(await file.read())

        result = process_video_file(temp_video_path)
        result["video_name"] = file.filename
        return result

    except Exception as e:
        logger.error(f"分析视频文件失败: {e}")
        raise_internal_error("分析视频文件失败", exc=e)
    finally:
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
