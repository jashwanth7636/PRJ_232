// ============================================================
// VOLTSAGE AI — SUBSTATION MAINTENANCE COPILOT CONTROLLER
// Conversation management, persistent sidebar, markdown & citations
// ============================================================

const API_URL = (window.location.protocol.startsWith("http") && window.location.port === "8000")
    ? "/chat"
    : "http://127.0.0.1:8000/chat";

let currentConversationId = localStorage.getItem("voltsage_active_conv") || null;
let allConversations = [];
let conversationHistory = []; // In-memory context for current session

const input = document.getElementById("maintenance-input");
const sendButton = document.getElementById("send-message");
const chatMessages = document.querySelector(".chat-messages");
const convsListEl = document.getElementById("conversations-list");
const convSearchInput = document.getElementById("conv-search-input");
const activeConvTitleEl = document.getElementById("active-conversation-title");

document.addEventListener("DOMContentLoaded", async function() {
    setupChatListeners();
    await loadUserConversations();

    if (currentConversationId) {
        await loadConversationDetails(currentConversationId);
    }
});

function setupChatListeners() {
    if (sendButton) {
        sendButton.addEventListener("click", sendMessage);
    }

    if (input) {
        input.addEventListener("keydown", function(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    const newChatBtn = document.getElementById("new-chat-btn");
    if (newChatBtn) {
        newChatBtn.addEventListener("click", startNewChat);
    }

    if (convSearchInput) {
        convSearchInput.addEventListener("input", function() {
            renderConversationsList();
        });
    }

    // Quick prompt pills
    document.querySelectorAll("[data-question]").forEach(btn => {
        btn.addEventListener("click", function() {
            if (input) {
                input.value = this.dataset.question;
                sendMessage();
            }
        });
    });
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
}

function formatMessage(text) {
    if (!text) return "";
    let safe = escapeHtml(text);

    // Bold **text**
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Lists and paragraphs
    const lines = safe.split("\n");
    let inUl = false;
    let inOl = false;
    let result = [];

    for (let line of lines) {
        const trimmed = line.trim();
        const bulletMatch = trimmed.match(/^(\*|-|•)\s+(.*)/);
        const numberMatch = trimmed.match(/^(\d+)\.\s+(.*)/);

        if (bulletMatch) {
            if (inOl) { result.push("</ol>"); inOl = false; }
            if (!inUl) { result.push("<ul>"); inUl = true; }
            result.push(`<li>${bulletMatch[2]}</li>`);
        } else if (numberMatch) {
            if (inUl) { result.push("</ul>"); inUl = false; }
            if (!inOl) { result.push("<ol>"); inOl = true; }
            result.push(`<li>${numberMatch[2]}</li>`);
        } else {
            if (inUl) { result.push("</ul>"); inUl = false; }
            if (inOl) { result.push("</ol>"); inOl = false; }
            if (trimmed.length > 0) {
                result.push(`<p>${trimmed}</p>`);
            }
        }
    }
    if (inUl) result.push("</ul>");
    if (inOl) result.push("</ol>");

    return result.join("");
}

function addMessage(text, type, sources = [], rawText = "") {
    if (!chatMessages) return;

    const message = document.createElement("div");
    const contentToCopy = rawText || text;

    let sourcesHTML = "";
    if (sources && sources.length > 0) {
        sourcesHTML = `<div class="sources-container">
            <span style="font-weight: 700; color: var(--accent-cyan); font-size: 11px;">Knowledge Sources:</span>` +
            sources.map(s => `<span class="source-badge">📄 ${escapeHtml(s.source)}</span>`).join("") +
        `</div>`;
    }

    if (type === "user") {
        message.className = "chat-message user";
        message.innerHTML = `
            <div class="message-avatar">US</div>
            <div style="display: flex; flex-direction: column; align-items: flex-end;">
                <div class="message-sender">User</div>
                <div class="message-bubble">
                    ${escapeHtml(text).replace(/\n/g, "<br>")}
                </div>
            </div>
        `;
    } else {
        message.className = "chat-message assistant";
        const copyId = "copy-" + Math.random().toString(36).substring(2, 9);
        message.innerHTML = `
            <div class="message-avatar">AI</div>
            <div style="display: flex; flex-direction: column; align-items: flex-start; max-width: 100%;">
                <div class="message-sender">VoltSage AI</div>
                <div class="message-bubble">
                    ${formatMessage(text)}
                    ${sourcesHTML}
                </div>
                <button type="button" class="copy-btn" id="${copyId}">
                    📋 Copy Response
                </button>
            </div>
        `;

        // Attach copy event listener
        setTimeout(() => {
            const btn = document.getElementById(copyId);
            if (btn) {
                btn.addEventListener("click", () => copyToClipboard(contentToCopy, btn));
            }
        }, 50);
    }

    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return message;
}

function copyToClipboard(text, btn) {
    if (!navigator.clipboard) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
        showCopiedFeedback(btn);
        return;
    }

    navigator.clipboard.writeText(text).then(() => {
        showCopiedFeedback(btn);
    }).catch(err => {
        console.error("Copy failed:", err);
    });
}

function showCopiedFeedback(btn) {
    const originalText = btn.innerHTML;
    btn.innerHTML = "✔ Copied!";
    btn.style.color = "var(--success)";
    btn.style.borderColor = "var(--success)";
    setTimeout(() => {
        btn.innerHTML = originalText;
        btn.style.color = "";
        btn.style.borderColor = "";
    }, 2000);
}

function addLoadingMessage() {
    if (!chatMessages) return null;
    const message = document.createElement("div");
    message.className = "chat-message assistant loading-message";
    message.innerHTML = `
        <div class="message-avatar">AI</div>
        <div style="display: flex; flex-direction: column; align-items: flex-start;">
            <div class="message-sender">VoltSage AI</div>
            <div class="message-bubble" style="color: var(--text-muted); display: flex; align-items: center; gap: 8px;">
                <span class="status-dot"></span> Consulting substation engineering manuals...
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
    if (!message) return;

    // Show user message
    addMessage(message, "user");
    input.value = "";
    input.disabled = true;
    if (sendButton) sendButton.disabled = true;

    const loadingEl = addLoadingMessage();

    try {
        const payload = {
            message: message,
            history: conversationHistory,
            conversation_id: currentConversationId
        };

        const res = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            credentials: "include"
        });

        if (!res.ok) {
            throw new Error(`Server returned HTTP ${res.status}`);
        }

        const data = await res.json();
        if (loadingEl) loadingEl.remove();

        // Display AI response
        addMessage(data.answer, "assistant", data.sources, data.answer);

        // Update active conversation
        if (data.conversation_id) {
            currentConversationId = data.conversation_id;
            localStorage.setItem("voltsage_active_conv", currentConversationId);
            await loadUserConversations();
            updateActiveConversationTitle();
        }

        conversationHistory.push({ role: "user", content: message });
        conversationHistory.push({ role: "assistant", content: data.answer });

    } catch (err) {
        console.error("Chat error:", err);
        if (loadingEl) loadingEl.remove();
        addMessage(
            "Sorry, could not connect to the VoltSage AI service. Please ensure the backend server is running on http://127.0.0.1:8000.",
            "assistant"
        );
    } finally {
        input.disabled = false;
        if (sendButton) sendButton.disabled = false;
        input.focus();
    }
}

// ============================================================
// CONVERSATIONS MANAGEMENT
// ============================================================

async function loadUserConversations() {
    if (!convsListEl) return;
    try {
        const res = await fetch("/api/conversations", { credentials: "include" });
        if (res.ok) {
            const data = await res.json();
            allConversations = data.conversations || [];
            renderConversationsList();
        } else if (res.status === 401) {
            // Unauthenticated guest state
            convsListEl.innerHTML = `
                <div style="padding: 16px 12px; text-align: center; color: var(--text-muted); font-size: 11.5px;">
                    <p style="margin-bottom: 8px;">Sign in to save and manage persistent conversation history.</p>
                    <a href="login.html?redirect=maintenance.html" class="btn btn-primary" style="padding: 4px 10px; font-size: 11px; width: 100%; justify-content: center;">Sign In</a>
                </div>
            `;
        }
    } catch (err) {
        console.warn("Could not load conversations:", err);
    }
}

function renderConversationsList() {
    if (!convsListEl || allConversations.length === 0) {
        if (convsListEl && !convsListEl.querySelector("a")) {
            convsListEl.innerHTML = `
                <div style="padding: 20px 10px; text-align: center; color: var(--text-muted); font-size: 12px;">
                    No recent conversations.
                </div>
            `;
        }
        return;
    }

    const query = convSearchInput?.value.toLowerCase().trim() || "";
    const filtered = allConversations.filter(c => !query || c.title.toLowerCase().includes(query));

    if (filtered.length === 0) {
        convsListEl.innerHTML = `
            <div style="padding: 16px 10px; text-align: center; color: var(--text-muted); font-size: 11.5px;">
                No matching conversations.
            </div>
        `;
        return;
    }

    let html = "";
    filtered.forEach(c => {
        const isActive = c.id === currentConversationId;
        html += `
            <div class="conv-item ${isActive ? 'active' : ''}" onclick="selectConversation('${c.id}')">
                <span class="conv-title" title="${escapeHtml(c.title)}">💬 ${escapeHtml(c.title)}</span>
                <div class="conv-actions">
                    <button type="button" class="conv-action-btn" title="Rename" onclick="event.stopPropagation(); renameConversation('${c.id}')">✏️</button>
                    <button type="button" class="conv-action-btn delete" title="Delete" onclick="event.stopPropagation(); deleteConversation('${c.id}')">🗑️</button>
                </div>
            </div>
        `;
    });

    convsListEl.innerHTML = html;
}

window.selectConversation = async function(convId) {
    currentConversationId = convId;
    localStorage.setItem("voltsage_active_conv", convId);
    renderConversationsList();
    await loadConversationDetails(convId);
};

async function loadConversationDetails(convId) {
    try {
        const res = await fetch(`/api/conversations/${convId}`, { credentials: "include" });
        if (!res.ok) {
            if (res.status === 404) {
                startNewChat();
            }
            return;
        }

        const data = await res.json();
        const conv = data.conversation;

        if (activeConvTitleEl) {
            activeConvTitleEl.textContent = conv.title;
        }

        // Clear chat screen and populate stored messages
        if (chatMessages) {
            chatMessages.innerHTML = "";
            conversationHistory = [];

            if (conv.messages && conv.messages.length > 0) {
                conv.messages.forEach(m => {
                    let sources = [];
                    if (m.sources) {
                        try { sources = JSON.parse(m.sources); } catch (e) {}
                    }
                    addMessage(m.content, m.role, sources, m.content);
                    conversationHistory.push({ role: m.role, content: m.content });
                });
            } else {
                renderWelcomeMessage();
            }
        }
    } catch (err) {
        console.error("Error loading conversation:", err);
    }
}

window.startNewChat = function() {
    currentConversationId = null;
    localStorage.removeItem("voltsage_active_conv");
    conversationHistory = [];

    if (activeConvTitleEl) {
        activeConvTitleEl.textContent = "New Substation Discussion";
    }

    renderConversationsList();
    renderWelcomeMessage();
};

function renderWelcomeMessage() {
    if (!chatMessages) return;
    chatMessages.innerHTML = `
        <div class="chat-message assistant">
            <div class="message-avatar">AI</div>
            <div style="display: flex; flex-direction: column; align-items: flex-start;">
                <div class="message-sender">VoltSage AI • Technical Copilot</div>
                <div class="message-bubble">
                    <p><strong>Welcome to VoltSage AI — Electrical Substation Copilot.</strong></p>
                    <p>I assist electrical engineers, technicians, and operators with substation equipment maintenance, fault diagnostics, and safety protocols grounded in indexed standards (IS 10028, IEEE C37, NEMA AB 4).</p>
                    <p style="margin-bottom: 0;">You can ask about:</p>
                    <ul style="margin-top: 6px;">
                        <li>Transformer Dissolved Gas Analysis (DGA), oil breakdown voltage testing (BDV), and conservator silica gel care</li>
                        <li>SF6 gas circuit breaker timing tests, contact resistance measurement, and lock-out/tag-out (LOTO) precautions</li>
                        <li>Busbar insulation, disconnect switch clearances, and protective relay testing (IS/IEC standards)</li>
                    </ul>
                </div>
            </div>
        </div>
    `;
}

window.renameConversation = async function(convId) {
    const current = allConversations.find(c => c.id === convId);
    const newTitle = prompt("Enter a new title for this conversation:", current ? current.title : "");
    if (!newTitle || !newTitle.trim()) return;

    try {
        const res = await fetch(`/api/conversations/${convId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: newTitle.trim() }),
            credentials: "include"
        });

        if (res.ok) {
            await loadUserConversations();
            if (currentConversationId === convId && activeConvTitleEl) {
                activeConvTitleEl.textContent = newTitle.trim();
            }
        } else {
            alert("Could not rename conversation.");
        }
    } catch (err) {
        console.error("Rename error:", err);
    }
};

window.deleteConversation = async function(convId) {
    if (!confirm("Are you sure you want to permanently delete this conversation and its messages?")) {
        return;
    }

    try {
        const res = await fetch(`/api/conversations/${convId}`, {
            method: "DELETE",
            credentials: "include"
        });

        if (res.ok) {
            if (currentConversationId === convId) {
                startNewChat();
            }
            await loadUserConversations();
        } else {
            alert("Could not delete conversation.");
        }
    } catch (err) {
        console.error("Delete error:", err);
    }
};

function updateActiveConversationTitle() {
    const conv = allConversations.find(c => c.id === currentConversationId);
    if (conv && activeConvTitleEl) {
        activeConvTitleEl.textContent = conv.title;
    }
}