const API_URL = "http://127.0.0.1:8000/chat";

const input = document.querySelector(
    'input[placeholder="Ask a maintenance question..."]'
);

const sendButton = document.querySelector(
    '.chat-input-area button'
);

const chatMessages = document.querySelector(
    '.chat-messages'
);

let conversationHistory = [];


function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}


function addMessage(text, type) {

    const message = document.createElement("div");

    message.className =
        `chat-message ${type}-message`;

    const avatar = document.createElement("div");

    avatar.className = "message-avatar";

    avatar.textContent =
        type === "user" ? "U" : "AI";


    const content = document.createElement("div");

    content.className = "message-content";

    content.innerHTML =
        escapeHtml(text).replace(/\n/g, "<br>");


    message.appendChild(avatar);
    message.appendChild(content);

    chatMessages.appendChild(message);

    chatMessages.scrollTop =
        chatMessages.scrollHeight;

    return message;
}


function addLoadingMessage() {

    const message = document.createElement("div");

    message.className =
        "chat-message assistant-message loading-message";

    message.innerHTML = `
        <div class="message-avatar">AI</div>

        <div class="message-content">
            Thinking...
        </div>
    `;

    chatMessages.appendChild(message);

    chatMessages.scrollTop =
        chatMessages.scrollHeight;

    return message;
}


async function sendMessage() {

    const message = input.value.trim();

    if (!message) {
        return;
    }


    // Show user message
    addMessage(message, "user");

    input.value = "";

    input.disabled = true;
    sendButton.disabled = true;


    // Show loading
    const loadingMessage =
        addLoadingMessage();


    try {

        const response = await fetch(
            API_URL, {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: message,
                    history: conversationHistory
                })
            }
        );


        if (!response.ok) {

            throw new Error(
                `Server error: ${response.status}`
            );
        }


        const data =
            await response.json();


        // Remove loading message
        loadingMessage.remove();


        // Display AI response
        addMessage(
            data.answer,
            "assistant"
        );


        // Save conversation
        conversationHistory.push({
            role: "user",
            content: message
        });


        conversationHistory.push({
            role: "assistant",
            content: data.answer
        });


    } catch (error) {

        console.error(error);

        loadingMessage.remove();

        addMessage(
            "Sorry, I couldn't connect to the AI server. Please make sure the FastAPI backend is running.",
            "assistant"
        );

    } finally {

        input.disabled = false;
        sendButton.disabled = false;

        input.focus();
    }
}


/* Send button */

if (sendButton) {

    sendButton.addEventListener(
        "click",
        sendMessage
    );
}


/* Enter key */

if (input) {

    input.addEventListener(
        "keydown",
        function(event) {

            if (event.key === "Enter") {

                event.preventDefault();

                sendMessage();
            }
        }
    );
}


/* Quick questions */

document.querySelectorAll(
    "[data-question]"
).forEach(button => {

    button.addEventListener(
        "click",
        function() {

            input.value =
                this.dataset.question;

            sendMessage();
        }
    );

});