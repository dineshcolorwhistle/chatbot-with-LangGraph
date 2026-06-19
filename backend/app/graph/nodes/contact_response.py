from typing import Dict, Any
from app.models.state import AgentState

async def contact_response_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles contact inquiries by returning a domain-specific email address.
    """
    namespace = state.get("namespace", "default")
    # Formulate domain-specific contact email
    contact_email = f"info@{namespace}.com"
    reply = f"You can reach our team directly at {contact_email} for detailed discussions. Alternatively, you can continue sharing your requirements here!"
    
    return {
        "reply": reply,
        "messages": state["messages"] + [{"role": "assistant", "content": reply}],
        "user_message_count": state.get("user_message_count", 0) + 1
    }
