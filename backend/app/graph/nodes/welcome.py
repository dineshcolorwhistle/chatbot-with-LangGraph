from typing import Dict, Any
from app.models.state import AgentState

async def welcome_node(state: AgentState) -> Dict[str, Any]:
    """
    Greets the client widget visitor and initiates conversation stage.
    """
    company_name = state.get("company_name", "our company")
    welcome_msg = f"Hello! 👋 I'm your AI consultant at {company_name}. How can I assist you with your project requirements or answer questions today?"
    
    return {
        "reply": welcome_msg,
        "stage": "conversation",
        "messages": state["messages"] + [{"role": "assistant", "content": welcome_msg}],
        "user_message_count": 0
    }
