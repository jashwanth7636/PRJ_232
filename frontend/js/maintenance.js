const API_URL = (window.location.protocol.startsWith("http") && window.location.port === "8000")
    ? "/chat"
    : "http://127.0.0.1:8000/chat";

const input = document.getElementById("maintenance-input") || document.querySelector(
    'input[placeholder="Ask a maintenance question..."]'
);

const sendButton = document.getElementById("send-message") || document.querySelector(
    '.chat-input-area button'
);

const chatMessages = document.querySelector(
    '.chat-messages'
);

let conversationHistory = [];


function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
}


function formatMessage(text) {
    if (!text) return "";
    let safe = escapeHtml(text);

    // Convert bold **text** to <strong>
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Process lists and paragraphs
    const lines = safe.split("\n");
    let inUl = false;
    let inOl = false;
    let result = [];

    for (let line of lines) {
        const trimmed = line.trim();
        const bulletMatch = trimmed.match(/^(\*|-|•)\s+(.*)/);
        const numberMatch = trimmed.match(/^(\d+)\.\s+(.*)/);

        if (bulletMatch) {
            if (inOl) {
                result.push("</ol>");
                inOl = false;
            }
            if (!inUl) {
                result.push("<ul>");
                inUl = true;
            }
            result.push(`<li>${bulletMatch[2]}</li>`);
        } else if (numberMatch) {
            if (inUl) {
                result.push("</ul>");
                inUl = false;
            }
            if (!inOl) {
                result.push("<ol>");
                inOl = true;
            }
            result.push(`<li>${numberMatch[2]}</li>`);
        } else {
            if (inUl) {
                result.push("</ul>");
                inUl = false;
            }
            if (inOl) {
                result.push("</ol>");
                inOl = false;
            }
            if (trimmed.length > 0) {
                result.push(`<p>${trimmed}</p>`);
            }
        }
    }
    if (inUl) result.push("</ul>");
    if (inOl) result.push("</ol>");

    return result.join("");
}


function addMessage(text, type, sources) {
    const message = document.createElement("div");

    let sourcesHTML = "";
    if (sources && sources.length > 0) {
        sourcesHTML = `<div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.08); font-size: 11px; color: #85858d;">
            <span style="font-weight: 600; color: #b9ff5c; margin-right: 6px;">Knowledge Source:</span>` +
            sources.map(s => `<span style="display: inline-block; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); padding: 2px 7px; border-radius: 6px; margin: 2px 4px 2px 0; color: #b5b5bc;">${escapeHtml(s.source)}</span>`).join("") +
        `</div>`;
    }

    if (type === "user") {
        message.className = "message user-message maintenance-message";
        message.style.cssText = "align-self: flex-end; justify-content: flex-end;";
        message.innerHTML = `
            <div class="message-content maintenance-message-content" style="text-align: right; max-width: 820px;">
                <div class="message-name maintenance-message-name" style="color: #8e8e96; text-align: right;">
                    Operator
                </div>
                <div class="message-text maintenance-message-text" style="background: rgba(185, 255, 92, 0.08); border-color: rgba(185, 255, 92, 0.22); color: #ffffff; text-align: left;">
                    ${escapeHtml(text).replace(/\n/g, "<br>")}
                </div>
            </div>
            <div class="message-avatar maintenance-message-avatar" style="background: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.15); color: #ffffff;">
                U
            </div>
        `;
    } else {
        message.className = "message assistant-message maintenance-message";
        message.innerHTML = `
            <div class="message-avatar maintenance-message-avatar">
                AI
            </div>
            <div class="message-content maintenance-message-content">
                <div class="message-name maintenance-message-name">
                    Substation AI
                </div>
                <div class="message-text maintenance-message-text">
                    ${formatMessage(text)}
                    ${sourcesHTML}
                </div>
            </div>
        `;
    }

    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return message;
}


function addLoadingMessage() {
    const message = document.createElement("div");
    message.className = "message assistant-message maintenance-message loading-message";
    message.innerHTML = `
        <div class="message-avatar maintenance-message-avatar">AI</div>
        <div class="message-content maintenance-message-content">
            <div class="message-name maintenance-message-name">Substation AI</div>
            <div class="message-text maintenance-message-text" style="color: #8e8e96; display: flex; align-items: center; gap: 8px;">
                <span class="status-dot" style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #b9ff5c;"></span> Consulting substation documentation...
            </div>
        </div>
    `;

    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return message;
}


async function sendMessage() {
    if (!input) return;
    const message = input.value.trim();

    if (!message) {
        return;
    }

    // Show user message
    addMessage(message, "user");

    input.value = "";
    input.disabled = true;
    if (sendButton) sendButton.disabled = true;

    // Show loading indicator
    const loadingMessage = addLoadingMessage();

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                history: conversationHistory
            })
        });

        if (!response.ok) {
            throw new Error(`Server returned HTTP ${response.status}`);
        }

        const data = await response.json();

        // Remove loading message
        loadingMessage.remove();

        // Display AI response with source documentation citations
        addMessage(data.answer, "assistant", data.sources);

        // Update conversation history
        conversationHistory.push({
            role: "user",
            content: message
        });

        conversationHistory.push({
            role: "assistant",
            content: data.answer
        });

    } catch (error) {
        console.error("Chat error:", error);
        loadingMessage.remove();

        addMessage(
            "Sorry, could not connect to the AI assistant backend. Please ensure the server is running on http://127.0.0.1:8000.",
            "assistant"
        );

    } finally {
        input.disabled = false;
        if (sendButton) sendButton.disabled = false;
        input.focus();
    }
}


/* Send button event */
if (sendButton) {
    sendButton.addEventListener("click", sendMessage);
}

/* Enter key event */
if (input) {
    input.addEventListener("keydown", function(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });
}

/* Quick question pills */
document.querySelectorAll("[data-question]").forEach(button => {
    button.addEventListener("click", function() {
        if (input) {
            input.value = this.dataset.question;
            sendMessage();
        }
    });
});