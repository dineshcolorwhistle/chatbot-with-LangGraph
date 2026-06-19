from typing import Dict, Any
from app.models.state import AgentState

async def off_topic_node(state: AgentState) -> Dict[str, Any]:
    """
    Politely redirects the user when they ask off-topic questions.
    """
    company_name = state.get("company_name", "our company")
    reply = f"I am here to help you with {company_name}'s services, expertise, and project requirements discovery. Could you please share more about your project needs or questions about our stack?"
    
    return {
        "reply": reply,
        "messages": state["messages"] + [{"role": "assistant", "content": reply}],
        "user_message_count": state.get("user_message_count", 0) + 1
    }
