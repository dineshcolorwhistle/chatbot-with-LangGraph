import logging
import asyncio
from typing import Dict, Any
from app.models.state import AgentState, CollectedData
from app.database import Database
from datetime import datetime

logger = logging.getLogger(__name__)

async def run_background_summary_and_email(state_dict: dict):
    """
    Asynchronous background worker task.
    Runs lead requirements summarization, stores lead in MongoDB,
    and sends SMTP notification emails to the admin and the visitor.
    """
    try:
        # Import services dynamically to avoid circular dependencies
        from app.services.summarization import SummarizationService
        from app.services.email_service import EmailService

        session_id = state_dict["session_id"]
        namespace = state_dict["namespace"]
        messages = state_dict["messages"]
        collected_data_dict = state_dict["collected_data"]
        
        # Rehydrate Pydantic model
        collected_data = CollectedData(**collected_data_dict)
        personal_info = collected_data.personal_info
        
        logger.info(f"🏁 Starting completed workflow for session: '{session_id}'")

        # 1. Generate requirements summary using LLM
        summary = await SummarizationService.generate_lead_summary(messages, collected_data)
        logger.info(f"📝 Requirements summary generated for session: '{session_id}'")

        # 2. Store Lead in MongoDB 'leads' collection
        leads_col = Database.get_leads_collection()
        lead_doc = {
            "session_id": session_id,
            "namespace": namespace,
            "personal_info": personal_info.model_dump(),
            "tech_discovery": collected_data.tech_discovery.model_dump(),
            "scope_pricing": collected_data.scope_pricing.model_dump(),
            "summary": summary,
            "created_at": datetime.utcnow()
        }
        await leads_col.insert_one(lead_doc)
        logger.info(f"💾 Saved lead document to MongoDB for session: '{session_id}'")

        # 3. Trigger Email Agent via SMTP (skip if email is missing)
        visitor_email = personal_info.email
        if visitor_email:
            # Send lead notification to business admin
            await EmailService.send_admin_notification(lead_doc)
            
            # Send thank you email to visitor
            await EmailService.send_visitor_thankyou(
                visitor_email=visitor_email,
                company_name=state_dict.get("company_name", "our company")
            )
            logger.info(f"📧 Admin notification and visitor thank you emails sent for: '{visitor_email}'")
        else:
            logger.info(f"⚠️ Visitor email not collected for session '{session_id}'. Skipping email notifications.")

    except Exception as e:
        logger.error(f"❌ Background completed node tasks failed for session '{state_dict.get('session_id')}': {e}", exc_info=True)

async def completed_node(state: AgentState) -> Dict[str, Any]:
    """
    Completed node. Fires background summarization and email notification tasks,
    then locks the conversation stage to 'completed'.
    """
    # Create serializable state snapshot for background thread safety
    serializable_state = {
        "session_id": state["session_id"],
        "namespace": state["namespace"],
        "company_name": state.get("company_name", ""),
        "messages": state["messages"],
        # Ensure collected_data is parsed to dictionary
        "collected_data": state["collected_data"].model_dump() if isinstance(state["collected_data"], CollectedData) else state["collected_data"]
    }
    
    # Fire and forget background tasks
    asyncio.create_task(run_background_summary_and_email(serializable_state))

    return {
        "reply": "Thank you! The session is closed. Our team will contact you shortly.",
        "stage": "completed"
    }
