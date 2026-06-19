import logging
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import ChatRequest, ChatResponse
from app.models.state import CollectedData
from app.graph.builder import compiled_graph
from app.utils.helpers import format_company_name, serialize_data
from app.database import Database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Chatbot"])

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main conversational endpoint. Ingests user message, runs LangGraph StateGraph,
    updates MongoDB history, and returns assistant reply.
    """
    session_id = request.session_id
    user_msg = request.message
    namespace = request.namespace or "default"
    
    # Configure the LangGraph checkpointer thread
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # 1. Fetch current state from memory checkpointer
        current_state = await compiled_graph.aget_state(config)
        
        # 2. If session is new, initialize variables and trigger welcome node
        if not current_state.values:
            initial_state = {
                "session_id": session_id,
                "namespace": namespace,
                "company_name": format_company_name(namespace),
                "stage": "welcome",
                "messages": [],
                "user_message_count": 0,
                "collected_data": CollectedData(),
                "reply": "",
                "data_collected": {}
            }
            
            # Initialize graph via welcome_node
            new_state = await compiled_graph.ainvoke(initial_state, config)
            
            return ChatResponse(
                reply=new_state["reply"],
                stage=new_state["stage"],
                data_collected=serialize_data(new_state["collected_data"])
            )
            
        # 3. Session exists. Ingest new user message into existing state history
        # Handle empty user message safely
        if not user_msg.strip():
            # If user sent empty message on an active session, return current reply
            return ChatResponse(
                reply=current_state.values.get("reply", ""),
                stage=current_state.values.get("stage", "conversation"),
                data_collected=serialize_data(current_state.values.get("collected_data", CollectedData()))
            )
            
        updated_messages = current_state.values["messages"] + [{"role": "user", "content": user_msg}]
        
        # 4. Invoke graph to run classification, routing, and conversation nodes
        updated_state = await compiled_graph.ainvoke(
            {"messages": updated_messages},
            config
        )
        
        return ChatResponse(
            reply=updated_state["reply"],
            stage=updated_state["stage"],
            data_collected=serialize_data(updated_state["collected_data"])
        )
        
    except Exception as e:
        logger.error(f"❌ Chat session '{session_id}' failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat: {str(e)}"
        )

@router.post("/reset")
async def reset_endpoint(request: ChatRequest):
    """
    Clears LangGraph state checkpointer and deletes MongoDB session history
    to provide a completely fresh session.
    """
    session_id = request.session_id
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # Overwrite state checkpointer with empty values
        await compiled_graph.aupdate_state(config, {
            "stage": "welcome",
            "messages": [],
            "user_message_count": 0,
            "collected_data": CollectedData(),
            "reply": "",
            "intent": "valid"
        })
        
        # Clear MongoDB chat_sessions collection for this session_id
        sessions_col = Database.get_sessions_collection()
        await sessions_col.delete_one({"session_id": session_id})
        
        logger.info(f"🔄 Reset session: '{session_id}'")
        return {"status": "success", "message": f"Session '{session_id}' has been reset."}
        
    except Exception as e:
        logger.error(f"❌ Reset session '{session_id}' failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reset failed: {str(e)}"
        )

@router.post("/exit")
async def exit_endpoint(request: ChatRequest):
    """
    Forcefully terminates the active session, updates stage to 'completed',
    and triggers lead extraction, summary generation, and email dispatches.
    """
    session_id = request.session_id
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        current_state = await compiled_graph.aget_state(config)
        if not current_state.values:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found."
            )
            
        # Update stage directly to 'completed'
        await compiled_graph.aupdate_state(config, {"stage": "completed"})
        
        # Invoke compiled_graph to execute completed_node workflow
        await compiled_graph.ainvoke(None, config)
        
        logger.info(f"🚪 Force exited session: '{session_id}'")
        return {"status": "success", "message": f"Session '{session_id}' has been closed."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Exit session '{session_id}' failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Exit failed: {str(e)}"
        )
