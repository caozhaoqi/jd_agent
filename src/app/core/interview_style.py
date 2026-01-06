from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from loguru import logger


class InterviewStyleType(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    MIXED = "mixed"
    STRICT = "strict"
    ENCOURAGING = "encouraging"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class QuestionType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SITUATIONAL = "situational"
    EXPERIENCE = "experience"
    PROBLEM_SOLVING = "problem_solving"
    CREATIVE = "creative"


class InterviewStyleConfig(BaseModel):
    style_type: InterviewStyleType = InterviewStyleType.PROFESSIONAL
    tone: str = "professional"
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    question_focus: List[QuestionType] = [QuestionType.TECHNICAL, QuestionType.BEHAVIORAL]
    follow_up_enabled: bool = True
    deep_dive_enabled: bool = True
    feedback_style: str = "constructive"
    probe_depth: int = 3
    allow_topic_branching: bool = True
    industry_specific: bool = False
    custom_instructions: Optional[str] = None
    
    class Config:
        use_enum_values = True


STYLE_PRESETS: Dict[str, InterviewStyleConfig] = {
    "professional": InterviewStyleConfig(
        style_type=InterviewStyleType.PROFESSIONAL,
        tone="formal",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_focus=[QuestionType.TECHNICAL, QuestionType.EXPERIENCE],
        follow_up_enabled=True,
        deep_dive_enabled=True,
        feedback_style="detailed",
        probe_depth=3,
        allow_topic_branching=False
    ),
    "casual": InterviewStyleConfig(
        style_type=InterviewStyleType.CASUAL,
        tone="friendly",
        difficulty=DifficultyLevel.BEGINNER,
        question_focus=[QuestionType.BEHAVIORAL, QuestionType.EXPERIENCE],
        follow_up_enabled=True,
        deep_dive_enabled=False,
        feedback_style="encouraging",
        probe_depth=2,
        allow_topic_branching=True
    ),
    "technical_deep": InterviewStyleConfig(
        style_type=InterviewStyleType.TECHNICAL,
        tone="technical",
        difficulty=DifficultyLevel.ADVANCED,
        question_focus=[QuestionType.TECHNICAL, QuestionType.PROBLEM_SOLVING],
        follow_up_enabled=True,
        deep_dive_enabled=True,
        feedback_style="technical",
        probe_depth=5,
        allow_topic_branching=True
    ),
    "behavioral_focus": InterviewStyleConfig(
        style_type=InterviewStyleType.BEHAVIORAL,
        tone="professional",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_focus=[QuestionType.BEHAVIORAL, QuestionType.SITUATIONAL],
        follow_up_enabled=True,
        deep_dive_enabled=True,
        feedback_style="insightful",
        probe_depth=4,
        allow_topic_branching=True
    ),
    "strict_evaluation": InterviewStyleConfig(
        style_type=InterviewStyleType.STRICT,
        tone="formal",
        difficulty=DifficultyLevel.EXPERT,
        question_focus=[QuestionType.TECHNICAL, QuestionType.PROBLEM_SOLVING, QuestionType.EXPERIENCE],
        follow_up_enabled=True,
        deep_dive_enabled=True,
        feedback_style="critical",
        probe_depth=5,
        allow_topic_branching=False
    ),
    "encouraging": InterviewStyleConfig(
        style_type=InterviewStyleType.ENCOURAGING,
        tone="supportive",
        difficulty=DifficultyLevel.BEGINNER,
        question_focus=[QuestionType.EXPERIENCE, QuestionType.BEHAVIORAL],
        follow_up_enabled=True,
        deep_dive_enabled=False,
        feedback_style="positive",
        probe_depth=2,
        allow_topic_branching=True
    ),
    "mixed": InterviewStyleConfig(
        style_type=InterviewStyleType.MIXED,
        tone="balanced",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_focus=[QuestionType.TECHNICAL, QuestionType.BEHAVIORAL, QuestionType.SITUATIONAL],
        follow_up_enabled=True,
        deep_dive_enabled=True,
        feedback_style="balanced",
        probe_depth=3,
        allow_topic_branching=True
    )
}


class InterviewStyleManager:
    def __init__(self):
        self.presets = STYLE_PRESETS
        logger.info("InterviewStyleManager initialized with {} presets".format(len(STYLE_PRESETS)))
    
    def get_preset(self, preset_name: str) -> Optional[InterviewStyleConfig]:
        return self.presets.get(preset_name.lower())
    
    def list_presets(self) -> List[str]:
        return list(self.presets.keys())
    
    def create_custom_style(
        self,
        name: str,
        base_preset: str = "professional",
        **overrides
    ) -> InterviewStyleConfig:
        base_config = self.get_preset(base_preset)
        if not base_config:
            base_config = self.presets["professional"]
        
        custom_config = base_config.model_copy(deep=True)
        
        for key, value in overrides.items():
            if hasattr(custom_config, key):
                setattr(custom_config, key, value)
        
        self.presets[name.lower()] = custom_config
        logger.info(f"Created custom interview style: {name}")
        
        return custom_config
    
    def generate_system_prompt(self, config: InterviewStyleConfig) -> str:
        style_guidance = {
            "professional": "Maintain a formal, professional tone throughout the interview.",
            "casual": "Keep the conversation relaxed and friendly.",
            "technical": "Focus on technical depth and precision in questions.",
            "behavioral": "Emphasize past experiences and behavioral patterns.",
            "mixed": "Balance technical and behavioral questions equally.",
            "strict": "Maintain high standards and rigorous evaluation criteria.",
            "encouraging": "Be supportive and encouraging to help candidates perform their best."
        }
        
        prompt_parts = [
            "You are conducting an AI-powered interview.",
            style_guidance.get(config.style_type, "Maintain a professional tone."),
        ]
        
        if config.difficulty == DifficultyLevel.BEGINNER:
            prompt_parts.append("Start with foundational questions and gradually increase complexity.")
        elif config.difficulty == DifficultyLevel.ADVANCED:
            prompt_parts.push("Include challenging questions that test deep expertise.")
        elif config.difficulty == DifficultyLevel.EXPERT:
            prompt_parts.append("Expect expert-level responses and probe deeply into complex scenarios.")
        
        if config.feedback_style == "constructive":
            prompt_parts.append("Provide constructive feedback after each major answer.")
        elif config.feedback_style == "detailed":
            prompt_parts.append("Give detailed analysis of candidate responses.")
        elif config.feedback_style == "technical":
            prompt_parts.append("Focus feedback on technical accuracy and depth.")
        elif config.feedback_style == "critical":
            prompt_parts.append("Be critical and thorough in evaluating responses.")
        elif config.feedback_style == "positive":
            prompt_parts.append("Emphasize positive aspects while gently noting areas for improvement.")
        
        if config.custom_instructions:
            prompt_parts.append(f"Additional guidelines: {config.custom_instructions}")
        
        return " ".join(prompt_parts)
    
    def get_style_for_position(self, position: str) -> InterviewStyleConfig:
        position_styles = {
            "software_engineer": "technical_deep",
            "frontend_developer": "technical_deep",
            "backend_developer": "technical_deep",
            "full_stack_developer": "mixed",
            "product_manager": "behavioral_focus",
            "data_scientist": "technical_deep",
            "devops_engineer": "technical_deep",
            "designer": "casual",
            "manager": "behavioral_focus",
            "analyst": "mixed"
        }
        
        position_lower = position.lower().replace(" ", "_")
        preset_name = position_styles.get(position_lower, "professional")
        
        return self.get_preset(preset_name) or self.get_preset("professional")


style_manager = InterviewStyleManager()
