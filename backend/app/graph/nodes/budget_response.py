from typing import Dict, Any
from app.models.state import AgentState

async def budget_response_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles budget/pricing queries by returning a strict team redirect message.
    """
    reply = "Our team will reach out and discuss about the budget with you."
    
    return {
        "reply": reply,
        "messages": state["messages"] + [{"role": "assistant", "content": reply}],
        "user_message_count": state.get("user_message_count", 0) + 1
    }
