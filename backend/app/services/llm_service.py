"""
MetricMind LLM & Deterministic Agent Service
Coordinates natural language question answering with deterministic fallback.
Prevents unconstrained SQL generation, verifies constraints, and ensures accurate execution.
"""
import logging
from ..config import settings
from ..models.schemas import ChatResponse
from .query_planner import plan_query
from .analytical_engine import execute_analytical_plan

logger = logging.getLogger(__name__)

def process_chat_question(question: str, conversation_id: str | None = None) -> ChatResponse:
    """
    Main entry point for business question analysis.
    Executes controlled semantic query planning and analytical execution.
    """
    # 1. Plan query deterministically against semantic registry
    plan = plan_query(question, conversation_id=conversation_id)
    
    # 2. Execute approved analytical plan against real dataset in SQLite
    response = execute_analytical_plan(plan, question)
    
    return response

def get_llm_status() -> dict:
    has_openai = bool(settings.OPENAI_API_KEY)
    has_anthropic = bool(settings.ANTHROPIC_API_KEY)
    has_gemini = bool(settings.GEMINI_API_KEY)
    
    active_engine = "Deterministic Semantic Query Engine (Built-in)"
    if has_gemini:
        active_engine = "Gemini AI + Deterministic Fallback"
    elif has_openai:
        active_engine = "OpenAI GPT-4o + Deterministic Fallback"
    elif has_anthropic:
        active_engine = "Anthropic Claude + Deterministic Fallback"
        
    return {
        "engine": active_engine,
        "openai_configured": has_openai,
        "anthropic_configured": has_anthropic,
        "gemini_configured": has_gemini,
        "deterministic_fallback_active": True
    }
