import os
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Dict, Any
import tempfile

from app.utils.video_utils import extract_audio_from_video, list_video_files
from openai import OpenAI
from app.core.config import settings

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

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"知识点分析失败: {e}")
        raise RuntimeError(f"知识点分析失败: {e}")


def generate_visual_summary(knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成可视化总结数据结构
    """
    # 这里可以根据需要扩展，生成适合前端可视化的数据格式
    # 例如：思维导图结构、知识点关联图等
    return {"type": "mind_map", "title": "课程知识点总结", "data": knowledge_data}


@router.post("/analyze-directory")
async def analyze_video_directory(directory_path: str = Form(...)):
    """
    分析指定目录下的所有视频文件，提取知识点并生成总结
    """
    if not os.path.exists(directory_path):
        raise HTTPException(status_code=404, detail="目录不存在")

    if not os.path.isdir(directory_path):
        raise HTTPException(status_code=400, detail="提供的路径不是目录")

    try:
        # 1. 列出目录中的所有视频文件
        video_files = list_video_files(directory_path)

        if not video_files:
            raise HTTPException(status_code=404, detail="目录中没有找到视频文件")

        results = []

        for video_path in video_files:
            try:
                # 2. 提取音频
                audio_path = extract_audio_from_video(video_path)

                # 3. 转录音频为文字
                transcript_text = transcribe_audio_file(audio_path)

                # 4. 分析关键知识点
                knowledge_data = analyze_key_knowledge(transcript_text)

                # 5. 生成可视化总结
                visual_summary = generate_visual_summary(knowledge_data)

                # 清理临时文件
                if os.path.exists(audio_path):
                    os.remove(audio_path)

                results.append(
                    {
                        "video_path": video_path,
                        "transcript": transcript_text,
                        "knowledge_points": knowledge_data,
                        "visual_summary": visual_summary,
                    }
                )
            except Exception as e:
                logger.error(f"处理视频文件失败 {video_path}: {e}")
                results.append({"video_path": video_path, "error": str(e)})

        return {
            "directory": directory_path,
            "total_videos": len(video_files),
            "processed_videos": len([r for r in results if "error" not in r]),
            "results": results,
        }

    except Exception as e:
        logger.error(f"分析视频目录失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析视频目录失败: {str(e)}")


@router.post("/analyze-video")
async def analyze_single_video(file: UploadFile = File(...)):
    """
    分析单个视频文件，提取知识点并生成总结
    """
    try:
        # 1. 保存上传的视频文件到临时位置
        temp_dir = tempfile.gettempdir()
        temp_video_path = os.path.join(temp_dir, file.filename)

        with open(temp_video_path, "wb") as f:
            f.write(await file.read())

        # 2. 提取音频
        audio_path = extract_audio_from_video(temp_video_path)

        # 3. 转录音频为文字
        transcript_text = transcribe_audio_file(audio_path)

        # 4. 分析关键知识点
        knowledge_data = analyze_key_knowledge(transcript_text)

        # 5. 生成可视化总结
        visual_summary = generate_visual_summary(knowledge_data)

        # 清理临时文件
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)

        return {
            "video_name": file.filename,
            "transcript": transcript_text,
            "knowledge_points": knowledge_data,
            "visual_summary": visual_summary,
        }

    except Exception as e:
        logger.error(f"分析视频文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析视频文件失败: {str(e)}")
