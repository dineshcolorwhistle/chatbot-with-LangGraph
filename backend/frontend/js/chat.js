/**
 * ==========================================================================
 * AI Agentic Chatbot Widget Client Library
 * Handles DOM building, Web API requests, session logs, and transitions.
 * ==========================================================================
 */

class ChatWidget {
    constructor(elementId) {
        // 1. Read attributes from document.currentScript (if loaded via script element)
        const currentScript = document.currentScript;
        let scriptApiUrl = "";
        let scriptNamespace = "";
        let scriptCompanyName = "";
        let scriptLogoUrl = "";
        let scriptPosition = "";

        if (currentScript) {
            scriptApiUrl = currentScript.getAttribute("data-api-url") || "";
            scriptNamespace = currentScript.getAttribute("data-namespace") || "";
            scriptCompanyName = currentScript.getAttribute("data-company-name") || "";
            scriptLogoUrl = currentScript.getAttribute("data-logo-url") || "";
            scriptPosition = currentScript.getAttribute("data-position") || "";
        }

        // 2. Locate or dynamically create the widget wrapper element
        this.element = document.getElementById(elementId);
        if (!this.element) {
            this.element = document.createElement("div");
            this.element.id = elementId;
            document.body.appendChild(this.element);
        }

        // 3. Set configurations, resolving div attribute overrides before script settings
        this.namespace = this.element.getAttribute("data-namespace") || scriptNamespace || "default";
        this.apiUrl = this.element.getAttribute("data-api-url") || scriptApiUrl || "";
        this.companyName = this.element.getAttribute("data-company-name") || scriptCompanyName || "";
        this.logoUrl = this.element.getAttribute("data-logo-url") || scriptLogoUrl || "";
        this.position = this.element.getAttribute("data-position") || scriptPosition || "bottom-right";

        // Clean trailing slash of API URL
        if (this.apiUrl) {
            this.apiUrl = this.apiUrl.replace(/\/$/, "");
        }

        // 4. Dynamically append the CSS stylesheet link if missing
        if (this.apiUrl) {
            const cssUrl = `${this.apiUrl}/widget/css/style.css`;
            if (!document.querySelector(`link[href="${cssUrl}"]`)) {
                const link = document.createElement("link");
                link.rel = "stylesheet";
                link.href = cssUrl;
                document.head.appendChild(link);
            }
        }

        // 5. Setup Session ID (UUID)
        this.sessionKey = `ai_chat_session_id_${this.namespace}`;
        this.sessionId = this.getOrCreateSessionId();

        // 6. Setup state variables
        this.isOpen = false;
        this.isTyping = false;
        this.messages = [];
        this.stage = "welcome";

        // 7. Initialize DOM and bind events
        this.buildWidgetDOM();
        this.bindEvents();
        
        // 8. Trigger welcome message if session is active or empty
        this.initChatSession();
    }

    getOrCreateSessionId() {
        let sid = localStorage.getItem(this.sessionKey);
        if (!sid) {
            sid = this.generateUUID();
            localStorage.setItem(this.sessionKey, sid);
        }
        return sid;
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    buildWidgetDOM() {
        // Create Floating Action Button (FAB)
        this.fab = document.createElement("div");
        this.fab.className = "chat-widget-fab";
        this.fab.innerHTML = `
            <svg viewBox="0 0 24 24">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
            </svg>
        `;

        // Create Chat Container Window
        this.container = document.createElement("div");
        this.container.className = "chat-widget-container";
        
        const avatarHTML = this.logoUrl ? `<img src="${this.logoUrl}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;">` : `🤖`;
        const titleText = this.companyName ? `${this.companyName} Consultant` : `Project Consultant`;

        this.container.innerHTML = `
            <div class="chat-widget-header">
                <div class="chat-header-info">
                    <div class="chat-header-avatar">${avatarHTML}</div>
                    <div class="chat-header-text">
                        <span class="chat-header-title">${titleText}</span>
                        <span class="chat-header-status">
                            <span class="chat-status-dot"></span> Online
                        </span>
                    </div>
                </div>
                <div class="chat-header-actions">
                    <button class="chat-header-btn" id="chat-btn-reset" title="Reset Session">
                        <svg viewBox="0 0 24 24"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
                    </button>
                    <button class="chat-header-btn" id="chat-btn-exit" title="Submit & Exit">
                        <svg viewBox="0 0 24 24"><path d="M10.09 15.59L11.5 17l5-5-5-5-1.41 1.41L12.67 11H3v2h9.67l-2.58 2.59zM19 3H5c-1.11 0-2 .9-2 2v4h2V5h14v14H5v-4H3v4c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/></svg>
                    </button>
                </div>
            </div>
            
            <div class="chat-messages-log" id="chat-msg-log">
                <!-- Message bubbles added dynamically -->
            </div>
            
            <div class="chat-widget-footer">
                <div class="chat-input-wrapper">
                    <input type="text" class="chat-input-field" id="chat-input" placeholder="Type your project details..." autocomplete="off">
                </div>
                <button class="chat-send-btn" id="chat-send-btn">
                    <svg viewBox="0 0 24 24">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                    </svg>
                </button>
            </div>
        `;

        // Apply Custom Position Styles
        if (this.position === "bottom-left") {
            this.fab.style.right = "auto";
            this.fab.style.left = "30px";
            this.container.style.right = "auto";
            this.container.style.left = "30px";
        }

        // Append to parent widget element
        this.element.appendChild(this.fab);
        this.element.appendChild(this.container);

        // Cache child selectors
        this.msgLog = this.container.querySelector("#chat-msg-log");
        this.inputField = this.container.querySelector("#chat-input");
        this.sendBtn = this.container.querySelector("#chat-send-btn");
        this.resetBtn = this.container.querySelector("#chat-btn-reset");
        this.exitBtn = this.container.querySelector("#chat-btn-exit");
    }

    bindEvents() {
        // Toggle widget open/close state
        this.fab.addEventListener("click", () => this.toggleWidget());

        // Keyboard Enter sends message
        this.inputField.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                this.handleUserSubmit();
            }
        });

        // Click send icon
        this.sendBtn.addEventListener("click", () => this.handleUserSubmit());

        // Click header reset
        this.resetBtn.addEventListener("click", () => this.resetSession());

        // Click header exit/force submit
        this.exitBtn.addEventListener("click", () => this.exitSession());
    }

    toggleWidget() {
        this.isOpen = !this.isOpen;
        if (this.isOpen) {
            this.container.classList.add("open");
            this.fab.classList.add("open");
            this.inputField.focus();
            // Automatically scroll to bottom on open
            this.scrollToBottom();
        } else {
            this.container.classList.remove("open");
            this.fab.classList.remove("open");
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.msgLog.scrollTop = this.msgLog.scrollHeight;
        }, 50);
    }

    showTypingIndicator() {
        if (this.isTyping) return;
        this.isTyping = true;
        
        this.typingBubble = document.createElement("div");
        this.typingBubble.className = "chat-typing-bubble";
        this.typingBubble.innerHTML = `
            <div class="chat-typing-dot"></div>
            <div class="chat-typing-dot"></div>
            <div class="chat-typing-dot"></div>
        `;
        
        this.msgLog.appendChild(this.typingBubble);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        if (!this.isTyping) return;
        this.isTyping = false;
        if (this.typingBubble && this.typingBubble.parentNode) {
            this.typingBubble.parentNode.removeChild(this.typingBubble);
        }
    }

    addMessageBubble(role, content) {
        const wrapper = document.createElement("div");
        wrapper.className = `chat-bubble-wrapper ${role}`;
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Clean line breaks inside message
        const formattedContent = content.replace(/\n/g, "<br>");

        wrapper.innerHTML = `
            <div class="chat-bubble">
                ${formattedContent}
            </div>
            <div class="chat-bubble-meta">${timestamp}</div>
        `;

        this.msgLog.appendChild(wrapper);
        this.scrollToBottom();
    }

    async initChatSession() {
        // Check if messages already exist in DOM, if empty fetch welcome init
        if (this.msgLog.children.length === 0) {
            await this.callChatAPI("");
        }
    }

    async handleUserSubmit() {
        const text = this.inputField.value.trim();
        if (!text || this.isTyping) return;

        // Reset input value
        this.inputField.value = "";

        // 1. Render message locally
        this.addMessageBubble("user", text);

        // 2. Call backend route
        await this.callChatAPI(text);
    }

    async callChatAPI(userMessage) {
        this.showTypingIndicator();

        const endpoint = `${this.apiUrl}/api/chat`;
        const payload = {
            session_id: this.sessionId,
            message: userMessage,
            namespace: this.namespace
        };

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`Server returned HTTP status ${response.status}`);
            }

            const data = await response.json();
            this.hideTypingIndicator();

            // Render chatbot reply bubble
            if (data.reply) {
                this.addMessageBubble("assistant", data.reply);
                this.stage = data.stage;
                
                // If session is closed, disable input field
                if (this.stage === "completed") {
                    this.disableInputField("Session closed. Details saved.");
                }
            }

        } catch (error) {
            console.error("❌ Widget communication failure:", error);
            this.hideTypingIndicator();
            this.addMessageBubble("assistant", "⚠️ Connection error. Please ensure the backend server is running and try again.");
        }
    }

    async resetSession() {
        if (!confirm("Are you sure you want to reset this chat session? All current progress will be lost.")) {
            return;
        }

        this.showTypingIndicator();
        const endpoint = `${this.apiUrl}/api/reset`;
        const payload = { session_id: this.sessionId, message: "", namespace: this.namespace };

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                // Clear localStorage ID, generate a new one
                localStorage.removeItem(this.sessionKey);
                this.sessionId = this.getOrCreateSessionId();
                
                // Clear log window
                this.msgLog.innerHTML = "";
                this.hideTypingIndicator();
                
                // Re-enable input if it was disabled
                this.enableInputField();

                // Trigger new welcome message
                await this.initChatSession();
            }
        } catch (e) {
            console.error("❌ Failed to reset session:", e);
            this.hideTypingIndicator();
        }
    }

    async exitSession() {
        if (this.stage === "completed") {
            alert("This session is already closed.");
            return;
        }

        if (!confirm("Would you like to finish and submit your requirements now? This will close the chat.")) {
            return;
        }

        this.showTypingIndicator();
        const endpoint = `${this.apiUrl}/api/exit`;
        const payload = { session_id: this.sessionId, message: "", namespace: this.namespace };

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                this.hideTypingIndicator();
                this.stage = "completed";
                this.addMessageBubble("assistant", "🏁 Thank you! Session closed. Our team has been notified and we will follow up shortly.");
                this.disableInputField("Session closed.");
            }
        } catch (e) {
            console.error("❌ Exit session failed:", e);
            this.hideTypingIndicator();
        }
    }

    disableInputField(placeholderText) {
        this.inputField.disabled = true;
        this.inputField.placeholder = placeholderText || "Session closed.";
        this.sendBtn.disabled = true;
        this.sendBtn.style.opacity = "0.5";
    }

    enableInputField() {
        this.inputField.disabled = false;
        this.inputField.placeholder = "Type your project details...";
        this.sendBtn.disabled = false;
        this.sendBtn.style.opacity = "1";
    }
}

// Instantiate widget on load
document.addEventListener("DOMContentLoaded", () => {
    window.aiChatWidgetInstance = new ChatWidget("ai-chat-widget");
});
