import logging
from typing import List, Dict
from app.models.state import CollectedData
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

SUMMARIZATION_SYSTEM_PROMPT = """
You are an expert Project Requirements Analyst.
Your task is to analyze a conversation log and any structured data collected from a visitor.
Produce a professional, structured, bullet-pointed requirements specification and lead summary in Markdown format.

Structure your response into the following clear sections:
1. **Lead Information**: (Name, Email, Company, Location - mention if any details are missing)
2. **Project Concept**: (Project type, core purpose, and target audience)
3. **Technical Specs**: (Tech stack, key features, and desired integrations)
4. **Scope & Deployment**: (Project timeline, MVP or full production target, and priority features)
5. **Key Conversation Takeaways**: (A 2-3 sentence summary highlighting user pain points, specific constraints, or direct requests)

Output ONLY the structured Markdown document. Do not include conversational greetings, signatures, or notes.
"""

class SummarizationService:
    """
    Service to generate structured requirements summaries from chat logs.
    """

    @classmethod
    async def generate_lead_summary(cls, messages: List[Dict[str, str]], collected_data: CollectedData) -> str:
        """
        Invokes LLM to analyze the conversation history and generate a markdown lead summary.
        """
        # Format conversation history for LLM readability
        chat_log = []
        for msg in messages:
            role = "Visitor" if msg["role"] == "user" else "Consultant"
            chat_log.append(f"{role}: {msg['content']}")
        
        chat_log_str = "\n".join(chat_log)

        # Format collected data fields
        structured_data_str = (
            f"PERSONAL INFO:\n{collected_data.personal_info.model_dump_json(indent=2)}\n\n"
            f"TECH DISCOVERY:\n{collected_data.tech_discovery.model_dump_json(indent=2)}\n\n"
            f"SCOPE & PRICING:\n{collected_data.scope_pricing.model_dump_json(indent=2)}"
        )

        user_input_payload = (
            f"--- CONVERSATION LOGS ---\n{chat_log_str}\n\n"
            f"--- STRUCTURED COLLECTED DATA ---\n{structured_data_str}"
        )

        try:
            summary = await LLMService.call_llm_simple(
                system_prompt=SUMMARIZATION_SYSTEM_PROMPT,
                user_message=user_input_payload,
                temperature=0.3
            )
            return summary.strip()
        except Exception as e:
            logger.error(f"❌ Failed to generate lead requirements summary: {e}")
            # Fallback output
            return (
                "### Project Requirements Summary (Extraction Fallback)\n"
                "- Lead Email: " + (collected_data.personal_info.email or "Not Provided") + "\n"
                "- Project Type: " + (collected_data.tech_discovery.project_type or "Not Provided") + "\n"
                "- Timeline: " + (collected_data.scope_pricing.timeline or "Not Provided") + "\n"
                "- Details: Please check MongoDB chat_sessions log for full transcript."
            )
