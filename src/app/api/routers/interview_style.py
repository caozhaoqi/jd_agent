from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from core.interview_style import (
    InterviewStyleConfig,
    InterviewStyleType,
    DifficultyLevel,
    QuestionType,
    style_manager
)

router = APIRouter()


class CustomStyleRequest(BaseModel):
    name: str
    base_preset: str = "professional"
    style_type: Optional[str] = None
    tone: Optional[str] = None
    difficulty: Optional[str] = None
    question_focus: Optional[list] = None
    follow_up_enabled: Optional[bool] = None
    deep_dive_enabled: Optional[bool] = None
    feedback_style: Optional[str] = None
    probe_depth: Optional[int] = None
    allow_topic_branching: Optional[bool] = None
    custom_instructions: Optional[str] = None


@router.get("/styles/presets")
async def list_presets():
    return {"presets": style_manager.list_presets()}


@router.get("/styles/{preset_name}")
async def get_style(preset_name: str):
    config = style_manager.get_preset(preset_name)
    if not config:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")
    return config


@router.post("/styles/custom")
async def create_custom_style(request: CustomStyleRequest):
    overrides = {}
    for key, value in request.model_dump().items():
        if key not in ["name", "base_preset"] and value is not None:
            overrides[key] = value
    
    config = style_manager.create_custom_style(request.name, request.base_preset, **overrides)
    return config


@router.post("/styles/generate-prompt")
async def generate_prompt(preset_name: str):
    config = style_manager.get_preset(preset_name)
    if not config:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")
    return {"prompt": style_manager.generate_system_prompt(config)}


@router.get("/styles/position/{position_name}")
async def get_style_for_position(position_name: str):
    config = style_manager.get_style_for_position(position_name)
    return config


@router.get("/styles/types")
async def get_style_types():
    return {
        "style_types": [e.value for e in InterviewStyleType],
        "difficulty_levels": [e.value for e in DifficultyLevel],
        "question_types": [e.value for e in QuestionType]
    }
