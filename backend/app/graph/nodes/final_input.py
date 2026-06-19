import logging
from typing import Dict, Any
from app.models.state import AgentState, CollectedData
from app.services.llm_service import LLMService
from app.utils.helpers import merge_collected_data

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """
You are a lead data extraction bot.
Analyze the user's message and extract any personal details, project requirements, timelines, features, or stack mentioned.
Map the extracted details into the following JSON structure. If any field is not mentioned, represent it with an empty string:

{
  "personal_info": {
    "name": "extracted name or empty string",
    "email": "extracted email or empty string",
    "company": "extracted company name or empty string",
    "location": "extracted location or empty string"
  },
  "tech_discovery": {
    "project_type": "extracted project type or empty string",
    "tech_stack": "extracted tech stack or empty string",
    "features": "extracted features list or empty string",
    "integrations": "extracted integrations list or empty string"
  },
  "scope_pricing": {
    "timeline": "extracted timeline or empty string",
    "mvp_or_production": "extracted MVP or production or empty string",
    "priority_features": "extracted priority features or empty string"
  }
}

Do not add notes, reasoning, or markdown syntax. Output valid JSON only.
"""

async def final_input_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates final requirements input. Performs a single-pass extraction if details
    are provided, then updates collected data and sets stage to 'completed'.
    """
    messages = state.get("messages", [])
    last_user_msg = messages[-1]["content"] if messages else ""
    
    # 1. Check if user declined to share final details
    declined_keywords = ["no", "no thanks", "stop", "nope", "nothing", "exit", "n"]
    if last_user_msg.strip().lower() in declined_keywords:
        reply = "Thank you! I have closed this session. Our team will reach out to you shortly."
        return {
            "reply": reply,
            "stage": "completed",
            "messages": messages + [{"role": "assistant", "content": reply}]
        }
        
    # 2. Extract details from their final input message
    try:
        raw_output = await LLMService.call_llm_simple(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_message=last_user_msg,
            temperature=0.0
        )
        extracted = LLMService.clean_json_response(raw_output)
    except Exception as e:
        logger.error(f"❌ Final data extraction failed: {e}")
        extracted = {}

    current_collected = state.get("collected_data")
    if not isinstance(current_collected, CollectedData):
        current_collected = CollectedData()
        
    updated_collected = merge_collected_data(current_collected, extracted)
    
    reply = "Thank you for the details! We have saved everything and our team will get in touch soon."
    return {
        "reply": reply,
        "collected_data": updated_collected,
        "stage": "completed",
        "messages": messages + [{"role": "assistant", "content": reply}]
    }
