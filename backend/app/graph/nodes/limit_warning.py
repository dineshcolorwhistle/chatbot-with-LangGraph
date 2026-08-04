from typing import Dict, Any
from app.models.state import AgentState

async def limit_warning_node(state: AgentState) -> Dict[str, Any]:
    """
    Warns the visitor that they've hit the message limit and asks if they want to share final details.
    Transitions stage to 'final_input'.
    """
    warning_prompt = (
        "You've reached the maximum number of interactions for this session. "
        "If you'd like to provide additional details about your requirements, click **Yes**. "
        "You can submit all remaining requirements in a single message, and our team will get in touch with you."
    )
    
    current_reply = state.get("reply", "")
    if current_reply:
        full_reply = f"{current_reply}\n\n{warning_prompt}"
    else:
        full_reply = warning_prompt
        
    messages = state.get("messages", [])
    if messages and messages[-1].get("role") == "assistant":
        updated_messages = list(messages)
        updated_messages[-1] = {"role": "assistant", "content": full_reply}
    else:
        updated_messages = messages + [{"role": "assistant", "content": full_reply}]
        
    return {
        "reply": full_reply,
        "stage": "final_input",
        "messages": updated_messages
    }
