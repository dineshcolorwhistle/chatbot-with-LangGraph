# Chatbot Process Flow & Architecture Summary

This document provides a step-by-step technical breakdown of the multi-agent lead qualification chatbot. It tracks the complete process from the moment a user submits a question in the frontend widget to the final execution of backend completion tasks.

---

## Process Flow Diagram

```mermaid
graph TD
    %% Frontend Action
    subgraph Frontend [1. Client Widget / UI]
        UserMsg["User types message & hits Enter"]
        ChatWidgetCall["ChatWidget.callChatAPI()"]
        UserMsg --> ChatWidgetCall
    end

    %% FastAPI Backend Route
    subgraph BackendRoute [2. FastAPI API Router]
        ChatRoute["chat_endpoint() in chat.py"]
        GetState["compiled_graph.aget_state()"]
        NewSession{"Is Session New?"}
        InitState["Create initial State dictionary"]
        InvokeWelcome["compiled_graph.ainvoke(initial_state)"]
        AppendMsg["Append user message to state history"]
        InvokeGraph["compiled_graph.ainvoke() with updated messages"]
        
        ChatWidgetCall -->|POST /api/chat| ChatRoute
        ChatRoute --> GetState
        GetState --> NewSession
        NewSession -->|Yes| InitState
        InitState --> InvokeWelcome
        NewSession -->|No| AppendMsg
        AppendMsg --> InvokeGraph
    end

    %% LangGraph Routing
    subgraph LangGraphRoute [3. LangGraph Entry Routing]
        RouteByStage["route_by_stage() conditional entry point"]
        InvokeWelcome --> RouteByStage
        InvokeGraph --> RouteByStage
    end

    %% Graph Execution Path
    subgraph StateGraph [4. StateGraph Workflows]
        %% Welcome Stage
        NodeWelcome["welcome_node"]
        RouteByStage -->|stage == 'welcome'| NodeWelcome
        NodeWelcome -->|END Edge| EndStep1["Graph session step completes"]
        
        %% Conversation Stage
        NodeIntent["intent_classifier_node"]
        ClassifyIntent{"classify_intent() edge"}
        NodeOffTopic["off_topic_node"]
        NodeBudget["budget_response_node"]
        NodeContact["contact_response_node"]
        NodeRAG["rag_conversation_node"]
        CheckLimit{"check_message_limit() edge"}
        NodeWarning["limit_warning_node"]
        
        RouteByStage -->|stage == 'conversation'| NodeIntent
        NodeIntent --> ClassifyIntent
        ClassifyIntent -->|'off_topic'| NodeOffTopic
        ClassifyIntent -->|'budget'| NodeBudget
        ClassifyIntent -->|'contact'| NodeContact
        ClassifyIntent -->|'valid'| NodeRAG
        
        NodeOffTopic -->|END Edge| EndStep2["Graph session step completes"]
        NodeBudget -->|END Edge| EndStep2
        NodeContact -->|END Edge| EndStep2
        
        NodeRAG --> CheckLimit
        CheckLimit -->|'end' / under limit| EndStep3["Graph session step completes"]
        CheckLimit -->|'limit_warning' / over limit| NodeWarning
        NodeWarning -->|END Edge| EndStep4["Graph session step completes (stage set to 'final_input')"]

        %% Final Input Stage
        NodeFinalInput["final_input_node"]
        NodeCompleted["completed_node"]
        
        RouteByStage -->|stage == 'final_input'| NodeFinalInput
        NodeFinalInput --> NodeCompleted
        
        %% Completed Stage
        RouteByStage -->|stage == 'completed'| NodeCompleted
        NodeCompleted -->|END Edge| EndStep5["Graph session step completes"]
    end

    %% Post Completion Background Tasks
    subgraph BackgroundJob [5. Background Completion Worker]
        TaskCompleted["run_background_summary_and_email()"]
        Summarize["SummarizationService.generate_lead_summary()"]
        SaveMongoDB["Insert Lead to MongoDB 'leads' collection"]
        SendEmail["EmailService (Admin Alert & Thank You Email)"]
        
        NodeCompleted -->|asyncio.create_task()| TaskCompleted
        TaskCompleted --> Summarize
        Summarize --> SaveMongoDB
        SaveMongoDB --> SendEmail
    end
```

---

## Detailed Step-by-Step Execution

### Step 1: User Message Ingestion (Frontend UI)
*   **Location**: [chat.js](file:///c:/chatbot-with-LangGraph/backend/frontend/js/chat.js) within the [ChatWidget](file:///c:/chatbot-with-LangGraph/backend/frontend/js/chat.js#L8) class.
*   **What happens**: 
    1. The user inputs their text in the chatbot text input box and presses **Enter** or clicks the send button.
    2. [handleUserSubmit](file:///c:/chatbot-with-LangGraph/backend/frontend/js/chat.js#L258) captures the input, sanitizes it, and posts a chat message locally to the bubble log UI.
    3. It then triggers [callChatAPI](file:///c:/chatbot-with-LangGraph/backend/frontend/js/chat.js#L272) which makes a POST request to `/api/chat` with the payload:
        ```json
        {
          "session_id": "<UUID stored in localStorage>",
          "message": "<User's query string>",
          "namespace": "<Vector store isolation partition key>"
        }
        ```

### Step 2: FastAPI Routing & State Recovery
*   **Location**: [chat.py](file:///c:/chatbot-with-LangGraph/backend/app/routes/chat.py) -> [chat_endpoint](file:///c:/chatbot-with-LangGraph/backend/app/routes/chat.py#L12)
*   **What happens**:
    1. The API endpoint receives the `ChatRequest` containing the message, session ID, and namespace.
    2. It calls `await compiled_graph.aget_state(config)` with the checkpointer configuration `{"configurable": {"thread_id": session_id}}` to load the current session state from memory checkpointer.
    3. **If the session is fresh/new** (no state values exist):
        *   It defines an initial state dictionary (setting `stage="welcome"`, initializing message history `messages=[]`, and setting up a fresh `CollectedData` object).
        *   It calls `await compiled_graph.ainvoke(initial_state, config)` to trigger the welcome greeting.
    4. **If the session already exists**:
        *   It appends the new user message to the historical message list: `messages = current_messages + [{"role": "user", "content": user_msg}]`.
        *   It runs the graph using `await compiled_graph.ainvoke({"messages": updated_messages}, config)`.

### Step 3: LangGraph Conditional Entry Point Routing
*   **Location**: [builder.py](file:///c:/chatbot-with-LangGraph/backend/app/graph/builder.py#L32) and [routing.py](file:///c:/chatbot-with-LangGraph/backend/app/graph/edges/routing.py#L4)
*   **What happens**:
    1. The LangGraph StateGraph initializes execution by calling its conditional entry point function: [route_by_stage](file:///c:/chatbot-with-LangGraph/backend/app/graph/edges/routing.py#L4).
    2. This function checks the current `stage` string stored in the state:
        *   If `stage == "welcome"`, it routes the execution to the **`welcome`** node.
        *   If `stage == "conversation"`, it routes to the **`intent_classifier`** node.
        *   If `stage == "final_input"`, it routes to the **`final_input`** node.
        *   If `stage == "completed"`, it routes to the **`completed`** node.
        *   If `stage` is empty or undefined, it defaults to the **`welcome`** node.

### Step 4: Node Execution & Conditional Edges
Depending on the stage routed during Step 3, the graph enters one of the following node pathways:

#### Pathway A: Welcome greeting (`welcome` node)
*   **Node**: [welcome_node](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/welcome.py#L4)
*   **Processing**:
    1. Greets the visitor with a default welcome message incorporating the namespace's company name.
    2. Updates the state: sets `stage = "conversation"`, appends the greeting to `messages`, and returns the dictionary.
*   **Next step**: The graph reaches the edge `workflow.add_edge("welcome", END)` and returns the welcome reply immediately back to the client widget.

#### Pathway B: Conversation processing (`intent_classifier` node)
*   **Node**: [intent_classifier_node](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/intent_classifier.py#L18)
*   **Processing**:
    1. Extracts the last user message.
    2. Invokes the LLM to classify the user's intent into: `"off_topic"`, `"budget"`, `"contact"`, or `"valid"`.
    3. Saves this intent in the state's `intent` property.
*   **Edge Transition**: LangGraph checks the conditional edge [classify_intent](file:///c:/chatbot-with-LangGraph/backend/app/graph/edges/routing.py#L13) which routes based on the classified intent:
    *   **If `"off_topic"`** -> routes to [off_topic_node](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/off_topic.py#L4), which returns a polite redirection, increments the `user_message_count`, and goes to `END`.
    *   **If `"budget"`** -> routes to [budget_response_node](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/budget_response.py#L4), which returns the budget shield redirection message, increments the `user_message_count`, and goes to `END`.
    *   **If `"contact"`** -> routes to [contact_response_node](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/contact_response.py#L4), which returns the direct contact email information, increments the `user_message_count`, and goes to `END`.
    *   **If `"valid"`** -> routes to [rag_conversation_node](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/rag_conversation.py#L108).

#### Pathway C: Core Conversation Agent (`rag_conversation` node)
*   **Node**: [rag_conversation_node](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/rag_conversation.py#L108)
*   **Processing**:
    1. Queries the Pinecone vector index under the target namespace to fetch related context documents (RAG context).
    2. Prepares a prompt template specifying company details, RAG context data, and instructions for lead detail extraction.
    3. Calls the LLM to generate:
        *   A conversational response answering the user's question.
        *   A structured extraction of fields mapping to `personal_info`, `tech_discovery`, and `scope_pricing`.
    4. Merges newly extracted fields non-destructively into the existing `collected_data` object.
    5. Saves a copy of the updated thread history, user message count, and data values to the MongoDB `chat_sessions` collection.
*   **Edge Transition**: Passes to the conditional edge [check_message_limit](file:///c:/chatbot-with-LangGraph/backend/app/graph/edges/routing.py#L19):
    *   If `user_message_count` < `settings.MAX_USER_MESSAGES` -> returns `"end"`, routing to `END`.
    *   If `user_message_count` >= `settings.MAX_USER_MESSAGES` -> returns `"limit_warning"`, routing to [limit_warning_node](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/limit_warning.py#L4). This node appends the warning message, sets `stage = "final_input"`, and routes to `END`.

#### Pathway D: Final requirements collection (`final_input` node)
*   **Node**: [final_input_node](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/final_input.py#L37)
*   **Processing**:
    1. Evaluates the user's final input message after receiving the message limit warning.
    2. If the user declined (e.g. "no", "exit", "n"), it sets the reply, updates `stage = "completed"`, and transitions to the `completed` node.
    3. If the user provided additional details, it runs a single-pass extraction LLM call, merges details into `collected_data`, sets `stage = "completed"`, and transitions to the `completed` node.

---

## Step 5: Session Completion & Background Orchestration
*   **Node**: [completed_node](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/completed.py#L68)
*   **Processing**:
    1. Creates a serializable snapshot of the conversation state.
    2. Triggers the background task worker using `asyncio.create_task(run_background_summary_and_email(serializable_state))` so it doesn't block the API response.
    3. Returns the closing message to the user: *"Thank you! The session is closed. Our team will contact you shortly."* and locks the graph `stage` to `"completed"`.
*   **Background Worker Actions** ([run_background_summary_and_email](file:///c:/chatbot-with-LangGraph/backend/app/graph/nodes/completed.py#L10)):
    1. **Summary Generation**: Invokes `SummarizationService.generate_lead_summary` to compile all chat messages and structured specifications into a markdown project summary.
    2. **MongoDB Lead Creation**: Inserts a new document representing the captured lead into the MongoDB `leads` collection containing the session history, structured requirements, and LLM-generated summary blueprint.
    3. **Email Notification Dispatch**:
        *   If the user's email address was collected during the conversation, it sends:
            *   An admin alert notification containing the requirements summary sheet to the configured business inbox.
            *   A friendly thank-you email confirmation to the visitor.
        *   If no email address is present, the script skips the notification step and logs the session completion event.
