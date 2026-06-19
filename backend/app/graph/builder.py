from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.models.state import AgentState
from app.graph.nodes.welcome import welcome_node
from app.graph.nodes.intent_classifier import intent_classifier_node
from app.graph.nodes.off_topic import off_topic_node
from app.graph.nodes.budget_response import budget_response_node
from app.graph.nodes.contact_response import contact_response_node
from app.graph.nodes.rag_conversation import rag_conversation_node
from app.graph.nodes.limit_warning import limit_warning_node
from app.graph.nodes.final_input import final_input_node
from app.graph.nodes.completed import completed_node

from app.graph.edges.routing import route_by_stage, classify_intent, check_message_limit

# 1. Initialize StateGraph
workflow = StateGraph(AgentState)

# 2. Add Nodes
workflow.add_node("welcome", welcome_node)
workflow.add_node("intent_classifier", intent_classifier_node)
workflow.add_node("off_topic", off_topic_node)
workflow.add_node("budget_response", budget_response_node)
workflow.add_node("contact_response", contact_response_node)
workflow.add_node("rag_conversation", rag_conversation_node)
workflow.add_node("limit_warning", limit_warning_node)
workflow.add_node("final_input", final_input_node)
workflow.add_node("completed", completed_node)

# 3. Set Conditional Entry Point (Stage routing)
workflow.set_conditional_entry_point(
    route_by_stage,
    {
        "welcome": "welcome",
        "intent_classifier": "intent_classifier",
        "final_input": "final_input",
        "completed": "completed"
    }
)

# 4. Define Graph Flows and Conditional Edges

# Welcome node goes straight to end of that step
workflow.add_edge("welcome", END)

# Intent Classifier determines where to send user input
workflow.add_conditional_edges(
    "intent_classifier",
    classify_intent,
    {
        "off_topic": "off_topic",
        "budget": "budget_response",
        "contact": "contact_response",
        "valid": "rag_conversation"
    }
)

# Guardrail nodes output template text and end step
workflow.add_edge("off_topic", END)
workflow.add_edge("budget_response", END)
workflow.add_edge("contact_response", END)

# Main conversation logic checks limit warning after RAG response
workflow.add_conditional_edges(
    "rag_conversation",
    check_message_limit,
    {
        "limit_warning": "limit_warning",
        "end": END
    }
)

# Limit warning ends step, prompting final_input on next message
workflow.add_edge("limit_warning", END)

# Final input captures details and routes to backend completion tasks
workflow.add_edge("final_input", "completed")
workflow.add_edge("completed", END)

# 5. Compile the graph with MemorySaver checkpointer for thread-safe session tracking
checkpointer = MemorySaver()
compiled_graph = workflow.compile(checkpointer=checkpointer)
