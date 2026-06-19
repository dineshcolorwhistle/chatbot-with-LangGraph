import re
import logging
from typing import Dict, Any
from app.models.state import AgentState, CollectedData
from app.services.llm_service import LLMService
from app.services.pinecone_service import PineconeService
from app.utils.helpers import merge_collected_data
from app.database import Database
from datetime import datetime

logger = logging.getLogger(__name__)

# Base System Instructions
SYSTEM_PROMPT_TEMPLATE = """
You are a professional project consultant chatbot representing '{company_name}'.
Your goal is to answer the visitor's questions using ONLY the provided trained context and naturally discover and qualify them as a lead.

---
TRAINED CONTEXT DATA (RAG):
{rag_context}
---

CORE CONSTRAINTS:
1. ONLY answer questions using the TRAINED CONTEXT DATA above.
2. DO NOT answer general questions (e.g. weather, general math, jokes, generic coding queries, questions about other companies).
3. If the answer to the visitor's question cannot be found in the TRAINED CONTEXT DATA, you must politely reply that you only have information about {company_name}'s services, and ask them if they want to discuss their project requirements. Do not make up any facts or use pre-trained generic knowledge.
4. Keep answers concise, helpful, and professional.

DATA EXTRACTION GOAL:
You need to extract any details provided by the visitor in this conversation and map them to the following JSON structure:
- personal_info: name, email, company, location
- tech_discovery: project_type (e.g. mobile app, website, SaaS), tech_stack, features, integrations
- scope_pricing: timeline, mvp_or_production, priority_features (Ignore budget here)

CONVERSATIONAL BEHAVIOR:
- Continue the conversation naturally. Do not sound like an interrogator or a form.
- Ask friendly follow-up questions to fill in missing details from the categories above.
- If they ask about pricing or budget, remember that budget is handled separately. Just focus on scope and requirements.

OUTPUT FORMAT:
You MUST respond with a valid JSON object matching this structure EXACTLY. Do not wrap in markdown blocks, do not output notes:
{{
  "response": "Your conversational answer to the visitor, answering their query and naturally asking the next logical requirements question.",
  "extracted_data": {{
    "personal_info": {{
      "name": "extracted name or empty string",
      "email": "extracted email or empty string",
      "company": "extracted company name or empty string",
      "location": "extracted location or empty string"
    }},
    "tech_discovery": {{
      "project_type": "extracted project type or empty string",
      "tech_stack": "extracted tech stack or empty string",
      "features": "extracted features list or empty string",
      "integrations": "extracted integrations list or empty string"
    }},
    "scope_pricing": {{
      "timeline": "extracted timeline or empty string",
      "mvp_or_production": "extracted MVP or production or empty string",
      "priority_features": "extracted priority features or empty string"
    }}
  }}
}}
"""

def extract_regex_fallbacks(text: str) -> Dict[str, Any]:
    """
    Regex fallback parser to catch name or email if LLM fails to extract.
    """
    fallbacks = {
        "personal_info": {}
    }
    
    # 1. Email extraction regex
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    if email_match:
        fallbacks["personal_info"]["email"] = email_match.group(0).strip()
        
    # 2. Basic Name pattern fallback: "my name is [name]", "i am [name]"
    name_match = re.search(r"(?:my name is|i am)\s+([a-zA-Z\s]{2,20})", text, re.IGNORECASE)
    if name_match:
        # Split by common ending words
        name = name_match.group(1).split("and")[0].split("from")[0].strip()
        if len(name.split()) <= 3:  # Valid name constraint
            fallbacks["personal_info"]["name"] = name
            
    return fallbacks

def build_contact_nudge(collected_data: CollectedData) -> str:
    """
    Constructs a polite contact nudge reminding user of missing lead details.
    """
    missing_fields = []
    
    pi = collected_data.personal_info
    if not pi.name:
        missing_fields.append("Name")
    if not pi.email:
        missing_fields.append("Email")
    if not pi.company:
        missing_fields.append("Company Name")
        
    if missing_fields:
        fields_str = ", ".join(missing_fields)
        return f"By the way, before we conclude, could you please share your {fields_str} so our team can get in touch with you?"
    return ""

async def rag_conversation_node(state: AgentState) -> Dict[str, Any]:
    """
    Core conversation agent. Performs RAG query, calls LLM,
    parses extracted details, applies contact nudges, and saves to MongoDB.
    """
    messages = state["messages"]
    last_user_msg = messages[-1]["content"] if messages else ""
    namespace = state.get("namespace", "default")
    company_name = state.get("company_name", "our company")
    user_count = state.get("user_message_count", 0)

    # 1. Query Pinecone RAG for context
    rag_context = ""
    if last_user_msg:
        rag_context = await PineconeService.query_pinecone(last_user_msg, namespace=namespace)

    # 2. Build system instructions
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        company_name=company_name,
        rag_context=rag_context or "No specific trained context available."
    )

    # 3. Invoke LLM
    try:
        raw_output = await LLMService.call_llm(
            system_prompt=system_prompt,
            messages=messages,
            temperature=0.2
        )
        parsed = LLMService.clean_json_response(raw_output)
    except Exception as e:
        logger.error(f"❌ LLM generation or parsing failed: {e}")
        # Graceful fallback reply
        parsed = {
            "response": "Could you please tell me more about your project goals, features, and stack?",
            "extracted_data": {}
        }

    # 4. Extract data and perform regex fallbacks
    extracted_data = parsed.get("extracted_data", {})
    fallback_data = extract_regex_fallbacks(last_user_msg)
    
    # Merge regex fallbacks if LLM extraction was empty
    for category in ["personal_info"]:
        if category in fallback_data:
            extracted_data.setdefault(category, {})
            for k, v in fallback_data[category].items():
                if not extracted_data[category].get(k):
                    extracted_data[category][k] = v

    # 5. Merge collected data non-destructively
    current_collected = state.get("collected_data")
    if not isinstance(current_collected, CollectedData):
        # Fallback initialization if TypedDict values are raw dicts
        current_collected = CollectedData()
        
    updated_collected = merge_collected_data(current_collected, extracted_data)
    
    # 6. Contact Nudge on Index 4 (Message #5)
    reply = parsed.get("response", "")
    if user_count == 4:
        nudge = build_contact_nudge(updated_collected)
        if nudge:
            reply += f"\n\n{nudge}"

    new_messages = messages + [{"role": "assistant", "content": reply}]
    new_user_count = user_count + 1

    # 7. Persist session history directly to MongoDB 'chat_sessions'
    try:
        sessions_col = Database.get_sessions_collection()
        await sessions_col.update_one(
            {"session_id": state["session_id"]},
            {
                "$set": {
                    "namespace": namespace,
                    "stage": state.get("stage", "conversation"),
                    "messages": new_messages,
                    "collected_data": updated_collected.model_dump(),
                    "user_message_count": new_user_count,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        logger.info(f"💾 Persisted session '{state['session_id']}' to MongoDB")
    except Exception as e:
        logger.error(f"❌ Failed to persist session to MongoDB: {e}")

    return {
        "reply": reply,
        "collected_data": updated_collected,
        "messages": new_messages,
        "user_message_count": new_user_count
    }
