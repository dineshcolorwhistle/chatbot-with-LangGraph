import logging
from typing import Dict, Any
from app.models.state import AgentState
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an Intent Classifier Agent. Your only job is to classify the user's latest message into one of four categories:
1. 'off_topic': Questions about weather, time, math, jokes, bot identity, general chat, or generic topics not related to the company's business or services.
2. 'budget': Questions about project costs, pricing, budget estimates, rates, or pricing plans.
3. 'contact': Inquiries about contact details, email addresses, phone numbers, location, address, or how to contact the team.
4. 'valid': Questions about project scope, technology stack, company services, features, integrations, case studies, or requirements.

You must respond with EXACTLY one of these four words: 'off_topic', 'budget', 'contact', 'valid'. Do not output any punctuation, reasoning, or formatting.
"""

async def intent_classifier_node(state: AgentState) -> Dict[str, Any]:
    """
    Invokes the Intent Classifier Agent to evaluate user message content.
    Returns classified intent in the state.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "valid"}

    # Get the last user message
    last_user_msg = messages[-1]["content"]
    
    try:
        raw_intent = await LLMService.call_llm_simple(
            system_prompt=SYSTEM_PROMPT,
            user_message=last_user_msg,
            temperature=0.0
        )
        
        # Clean the response to match classification list
        intent = raw_intent.strip().lower()
        if intent not in ["off_topic", "budget", "contact", "valid"]:
            logger.warning(f"⚠️ Unexpected intent classifier output: '{raw_intent}'. Defaulting to 'valid'.")
            intent = "valid"
            
    except Exception as e:
        logger.error(f"❌ Intent classification failed: {e}. Defaulting to 'valid'.")
        intent = "valid"

    logger.info(f"🔍 Classified message intent: '{intent}' (User message: '{last_user_msg}')")
    return {"intent": intent}
