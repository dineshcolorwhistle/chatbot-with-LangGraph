from typing import Dict, Any
from app.models.state import AgentState

async def limit_warning_node(state: AgentState) -> Dict[str, Any]:
    """
    Warns the visitor that they've hit the message limit and asks if they want to share final details.
    Transitions stage to 'final_input'.
    """
    warning_msg = (
        "We've reached our conversation limit for this session. "
        "Would you like to provide any final requirements or contact details before we submit? (Yes/No)"
    )
    
    return {
        "reply": warning_msg,
        "stage": "final_input",
        "messages": state["messages"] + [{"role": "assistant", "content": warning_msg}]
    }
