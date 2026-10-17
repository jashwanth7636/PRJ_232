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
            sources.map(s => {
                const title = typeof s === "string" ? s : (s.source || "");
                const pageNum = (typeof s === "object" && s.page) ? s.page : null;
                const pageLabel = pageNum ? ` (Page ${escapeHtml(String(pageNum))})` : "";
                return `<span class="source-badge">📄 ${escapeHtml(title)}${pageLabel}</span>`;
            }).join("") +
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

let currentStreamAbort = null;

function addLoadingMessage() {
    if (!chatMessages) return null;
    const message = document.createElement("div");
    message.className = "chat-message assistant loading-message";
    message.innerHTML = `
        <div class="message-avatar">AI</div>
        <div style="display: flex; flex-direction: column; align-items: flex-start;">
            <div class="message-sender">VoltSage AI</div>
            <div class="message-bubble" style="color: var(--text-muted); display: flex; align-items: center; gap: 8px;">
                <span class="status-dot"></span> VoltSage AI is thinking...
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

    // Abort any ongoing stream if user sends repeated message
    if (currentStreamAbort) {
        currentStreamAbort.abort();
        currentStreamAbort = null;
    }

    const abortController = new AbortController();
    currentStreamAbort = abortController;

    // Show user message
    addMessage(message, "user");
    input.value = "";
    input.disabled = true;
    if (sendButton) sendButton.disabled = true;

    const thinkingEl = addLoadingMessage();

    let assistantMessageEl = null;
    let bubbleEl = null;
    let copyBtnEl = null;
    let streamedText = "";
    let finalSources = [];
    let newConvId = null;

    try {
        const payload = {
            message: message,
            history: conversationHistory,
            conversation_id: currentConversationId
        };

        const res = await fetch("/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            credentials: "include",
            signal: abortController.signal
        });

        if (!res.ok) {
            throw new Error(`Server returned HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const events = buffer.split("\n\n");
            buffer = events.pop(); // keep trailing incomplete chunk

            for (const eventBlock of events) {
                if (!eventBlock.trim()) continue;

                let eventName = "message";
                let dataStr = "";

                for (const line of eventBlock.split("\n")) {
                    if (line.startsWith("event:")) {
                        eventName = line.substring(6).trim();
                    } else if (line.startsWith("data:")) {
                        dataStr = line.substring(5).trim();
                    }
                }

                if (!dataStr) continue;

                let data;
                try {
                    data = JSON.parse(dataStr);
                } catch (e) {
                    continue;
                }

                if (eventName === "start") {
                    if (data.conversation_id) {
                        newConvId = data.conversation_id;
                    }
                } else if (eventName === "chunk") {
                    // First chunk: immediately remove thinking message
                    if (thinkingEl && thinkingEl.parentNode) {
                        thinkingEl.remove();
                    }

                    if (!assistantMessageEl) {
                        assistantMessageEl = document.createElement("div");
                        assistantMessageEl.className = "chat-message assistant";
                        const copyId = "copy-" + Math.random().toString(36).substring(2, 9);
                        assistantMessageEl.innerHTML = `
                            <div class="message-avatar">AI</div>
                            <div style="display: flex; flex-direction: column; align-items: flex-start; max-width: 100%; width: 100%;">
                                <div class="message-sender">VoltSage AI</div>
                                <div class="message-bubble"></div>
                                <button type="button" class="copy-btn" id="${copyId}" style="display: none;">
                                    📋 Copy Response
                                </button>
                            </div>
                        `;
                        chatMessages.appendChild(assistantMessageEl);
                        bubbleEl = assistantMessageEl.querySelector(".message-bubble");
                        copyBtnEl = assistantMessageEl.querySelector(".copy-btn");
                    }

                    streamedText += data.text || "";
                    bubbleEl.innerHTML = formatMessage(streamedText);
                    chatMessages.scrollTop = chatMessages.scrollHeight;

                } else if (eventName === "done") {
                    if (data.sources) {
                        finalSources = data.sources;
                    }
                    if (data.conversation_id) {
                        newConvId = data.conversation_id;
                    }
                    if (data.full_text && !streamedText) {
                        streamedText = data.full_text;
                        if (bubbleEl) {
                            bubbleEl.innerHTML = formatMessage(streamedText);
                        }
                    }
                } else if (eventName === "error") {
                    throw new Error(data.error || "Generation error");
                }
            }
        }

        // Remove thinking element if it wasn't removed yet
        if (thinkingEl && thinkingEl.parentNode) {
            thinkingEl.remove();
        }

        if (!assistantMessageEl && streamedText) {
            addMessage(streamedText, "assistant", finalSources, streamedText);
        } else if (bubbleEl) {
            // Append sources to the bubble
            if (finalSources && finalSources.length > 0) {
                const sourcesHTML = `<div class="sources-container">
                    <span style="font-weight: 700; color: var(--accent-cyan); font-size: 11px;">Knowledge Sources:</span>` +
                    finalSources.map(s => {
                        const title = typeof s === "string" ? s : (s.source || "");
                        const pageNum = (typeof s === "object" && s.page) ? s.page : null;
                        const pageLabel = pageNum ? ` (Page ${escapeHtml(String(pageNum))})` : "";
                        return `<span class="source-badge">📄 ${escapeHtml(title)}${pageLabel}</span>`;
                    }).join("") +
                `</div>`;
                bubbleEl.insertAdjacentHTML("beforeend", sourcesHTML);
            }

            if (copyBtnEl) {
                copyBtnEl.style.display = "inline-flex";
                copyBtnEl.addEventListener("click", () => copyToClipboard(streamedText, copyBtnEl));
            }
        }

        // Update active conversation
        if (newConvId) {
            currentConversationId = newConvId;
            localStorage.setItem("voltsage_active_conv", currentConversationId);
            await loadUserConversations();
            updateActiveConversationTitle();
        }

        if (streamedText) {
            conversationHistory.push({ role: "user", content: message });
            conversationHistory.push({ role: "assistant", content: streamedText });
        }

    } catch (err) {
        if (err.name === "AbortError") {
            console.log("Chat stream aborted");
            return;
        }
        console.error("Chat error:", err);
        if (thinkingEl && thinkingEl.parentNode) {
            thinkingEl.remove();
        }
        if (!assistantMessageEl) {
            addMessage(
                "Sorry, could not connect to the VoltSage AI service. Please ensure the backend server is running on http://127.0.0.1:8000.",
                "assistant"
            );
        }
    } finally {
        currentStreamAbort = null;
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

function groupConversationsByDate(convs) {
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);

    const isSameDay = (d1, d2) =>
        d1.getFullYear() === d2.getFullYear() &&
        d1.getMonth() === d2.getMonth() &&
        d1.getDate() === d2.getDate();

    const groups = {
        today: [],
        yesterday: [],
        earlier: []
    };

    convs.forEach(c => {
        const rawDate = c.updated_at || c.created_at;
        const d = new Date(rawDate);
        if (isNaN(d.getTime())) {
            groups.earlier.push(c);
        } else if (isSameDay(d, today)) {
            groups.today.push(c);
        } else if (isSameDay(d, yesterday)) {
            groups.yesterday.push(c);
        } else {
            groups.earlier.push(c);
        }
    });

    return groups;
}

function renderConversationsList() {
    if (!convsListEl) return;

    if (allConversations.length === 0) {
        convsListEl.innerHTML = `
            <div style="padding: 24px 10px; text-align: center; color: var(--text-muted); font-size: 12px;">
                No recent conversations.<br>
                <span style="font-size: 11px; color: var(--accent-cyan); cursor: pointer;" onclick="startNewChat()">Start a new chat ⚡</span>
            </div>
        `;
        return;
    }

    const query = convSearchInput?.value.toLowerCase().trim() || "";
    const filtered = allConversations.filter(c => !query || (c.title && c.title.toLowerCase().includes(query)));

    if (filtered.length === 0) {
        convsListEl.innerHTML = `
            <div style="padding: 16px 10px; text-align: center; color: var(--text-muted); font-size: 11.5px;">
                No matching conversations.
            </div>
        `;
        return;
    }

    const groups = groupConversationsByDate(filtered);
    let html = "";

    const renderGroup = (label, list) => {
        if (!list || list.length === 0) return "";
        let groupHtml = `<div class="conv-group-header">${label}</div>`;
        list.forEach(c => {
            const isActive = c.id === currentConversationId;
            groupHtml += `
                <div class="conv-item ${isActive ? 'active' : ''}" onclick="selectConversation('${c.id}')">
                    <span class="conv-title" title="${escapeHtml(c.title)}">💬 ${escapeHtml(c.title)}</span>
                    <div class="conv-actions">
                        <button type="button" class="conv-action-btn" title="Rename" onclick="event.stopPropagation(); renameConversation('${c.id}')">✏️</button>
                        <button type="button" class="conv-action-btn delete" title="Delete" onclick="event.stopPropagation(); deleteConversation('${c.id}')">🗑️</button>
                    </div>
                </div>
            `;
        });
        return groupHtml;
    };

    html += renderGroup("TODAY", groups.today);
    html += renderGroup("YESTERDAY", groups.yesterday);
    html += renderGroup("EARLIER", groups.earlier);

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
        <div class="chat-welcome-container">
            <div class="welcome-icon-glow">⚡</div>
            <h1 class="welcome-title">Let’s solve substation maintenance challenges</h1>
            <p class="welcome-subtitle">
                Ask technical questions about high-voltage transformers, circuit breakers, busbar clearances, or protective relays. Technical responses are directly grounded in indexed maintenance standards (IS 10028, IEEE C37, NEMA AB 4).
            </p>

            <div class="welcome-prompt-grid">
                <div class="welcome-prompt-card" onclick="document.getElementById('maintenance-input').value='What are the safety precautions for circuit breaker maintenance?'; sendMessage();">
                    <div class="prompt-card-header">
                        <span>🛡️</span>
                        <span>Circuit Breaker Maintenance</span>
                    </div>
                    <p class="prompt-desc">Essential LOTO precautions, grounding procedures, and contact resistance limits.</p>
                </div>

                <div class="welcome-prompt-card" onclick="document.getElementById('maintenance-input').value='What causes Buchholz relay trips in power transformers?'; sendMessage();">
                    <div class="prompt-card-header">
                        <span>⚡</span>
                        <span>Transformer DGA & Buchholz</span>
                    </div>
                    <p class="prompt-desc">Internal arc gas accumulation, oil BDV dielectric breakdown, and moisture ingress.</p>
                </div>

                <div class="welcome-prompt-card" onclick="document.getElementById('maintenance-input').value='Explain the difference between LG, LL, LLG, and LLL symmetrical substation faults.'; sendMessage();">
                    <div class="prompt-card-header">
                        <span>🔍</span>
                        <span>3-Phase Fault Diagnosis</span>
                    </div>
                    <p class="prompt-desc">Symmetrical 3-phase faults vs asymmetrical line-to-ground characteristics.</p>
                </div>

                <div class="welcome-prompt-card" onclick="document.getElementById('maintenance-input').value='What are the inspection steps for SF6 gas circuit breakers?'; sendMessage();">
                    <div class="prompt-card-header">
                        <span>📋</span>
                        <span>SF6 Breaker Inspection</span>
                    </div>
                    <p class="prompt-desc">Density monitor pressure thresholds, gas moisture dew point, and leak detection.</p>
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