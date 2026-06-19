from app.models.state import AgentState
from app.config import settings

def route_by_stage(state: AgentState) -> str:
    """
    Evaluates current stage of the session and routes entry/invocation flow.
    """
    stage = state.get("stage", "welcome")
    if stage == "conversation":
        return "intent_classifier"
    return stage

def classify_intent(state: AgentState) -> str:
    """
    Routes to the correct node based on the classification result from the Intent Classifier.
    """
    return state.get("intent", "valid")

def check_message_limit(state: AgentState) -> str:
    """
    Determines if user has reached their maximum interaction limit for the session.
    """
    count = state.get("user_message_count", 0)
    if count >= settings.MAX_USER_MESSAGES:
        return "limit_warning"
    return "end"
