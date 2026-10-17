// ============================================================
// PRJ_232 — KNOWLEDGE BASE & DOCUMENT MANAGEMENT CONTROLLER
// Real-time document retrieval, live filtering & PDF upload
// ============================================================

let allDocuments = [];
let currentCategory = "All";

document.addEventListener("DOMContentLoaded", function() {
    loadDocuments();
    setupEventListeners();
});

function setupEventListeners() {
    // Search input
    const searchInput = document.getElementById("doc-search-input");
    if (searchInput) {
        searchInput.addEventListener("input", function() {
            filterAndRenderDocuments();
        });
    }

    // Category filter buttons
    document.querySelectorAll("[data-category]").forEach(btn => {
        btn.addEventListener("click", function() {
            document.querySelectorAll("[data-category]").forEach(b => b.classList.remove("active"));
            this.classList.add("active");
            currentCategory = this.dataset.category;
            filterAndRenderDocuments();
        });
    });

    // Upload form
    const uploadInput = document.getElementById("pdf-upload-input");
    const uploadBtn = document.getElementById("upload-submit-btn");
    if (uploadBtn && uploadInput) {
        uploadBtn.addEventListener("click", handleDocumentUpload);
    }

    // Upload dropzone drag/drop
    const dropzone = document.getElementById("upload-dropzone");
    if (dropzone && uploadInput) {
        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        });
        dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
            if (e.dataTransfer.files.length > 0) {
                uploadInput.files = e.dataTransfer.files;
                updateSelectedFilename();
            }
        });
        uploadInput.addEventListener("change", updateSelectedFilename);
    }
}

function updateSelectedFilename() {
    const uploadInput = document.getElementById("pdf-upload-input");
    const labelEl = document.getElementById("selected-file-label");
    if (labelEl && uploadInput && uploadInput.files.length > 0) {
        labelEl.textContent = `Selected: ${uploadInput.files[0].name} (${(uploadInput.files[0].size / (1024 * 1024)).toFixed(2)} MB)`;
        labelEl.style.color = "var(--accent-cyan)";
    }
}

async function loadDocuments() {
    const grid = document.getElementById("documents-grid");
    if (!grid) return;

    try {
        const res = await fetch("/api/documents");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        allDocuments = data.documents || [];

        // Update stats
        const totalDocsEl = document.getElementById("stat-total-docs");
        if (totalDocsEl) totalDocsEl.textContent = data.total_documents;

        const totalChunksEl = document.getElementById("stat-total-chunks");
        if (totalChunksEl) totalChunksEl.textContent = data.total_chunks;

        filterAndRenderDocuments();
    } catch (err) {
        console.error("Error loading documents:", err);
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">
                <p>Could not load document repository from server. Please ensure the backend is running.</p>
            </div>
        `;
    }
}

function filterAndRenderDocuments() {
    const grid = document.getElementById("documents-grid");
    if (!grid) return;

    const query = document.getElementById("doc-search-input")?.value.toLowerCase().trim() || "";

    const filtered = allDocuments.filter(doc => {
        const matchesCat = (currentCategory === "All") || (doc.category === currentCategory);
        const matchesQuery = !query || doc.name.toLowerCase().includes(query) || doc.category.toLowerCase().includes(query);
        return matchesCat && matchesQuery;
    });

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 48px 20px; background: var(--bg-card); border: 1px dashed var(--border-subtle); border-radius: var(--radius-lg);">
                <div style="font-size: 32px; margin-bottom: 12px; opacity: 0.6;">🔍</div>
                <h3 style="color: #fff; margin-bottom: 6px;">No matching documents found</h3>
                <p style="color: var(--text-muted); font-size: 13px;">Try adjusting your search query or upload a new engineering PDF.</p>
            </div>
        `;
        return;
    }

    let html = "";
    filtered.forEach(doc => {
        const icon = doc.category === "Transformers" ? "⚡" : (doc.category === "Circuit Breakers" ? "🛡️" : "◈");
        html += `
            <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
                        <span style="font-size: 10.5px; font-weight: 700; padding: 3px 8px; border-radius: 4px; background: rgba(0, 210, 255, 0.1); color: var(--accent-cyan); text-transform: uppercase;">${doc.category}</span>
                        <span style="font-size: 11px; font-weight: 700; color: var(--success); display: inline-flex; align-items: center; gap: 4px;">
                            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--success);"></span> ${doc.status}
                        </span>
                    </div>

                    <div style="display: flex; gap: 12px; align-items: flex-start; margin-bottom: 12px;">
                        <div style="width: 38px; height: 38px; border-radius: 8px; background: rgba(255, 255, 255, 0.04); display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;">${icon}</div>
                        <h3 style="font-size: 15px; color: #fff; line-height: 1.35; margin: 0;">${escapeHtml(doc.name)}</h3>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 12px; background: rgba(7, 11, 18, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); margin-bottom: 16px; font-size: 12px;">
                        <div>
                            <span style="color: var(--text-muted); display: block; font-size: 10.5px;">FILE SIZE</span>
                            <strong style="color: #fff;">${doc.size_mb} MB</strong>
                        </div>
                        <div>
                            <span style="color: var(--text-muted); display: block; font-size: 10.5px;">INDEXED CHUNKS</span>
                            <strong style="color: var(--accent-cyan);">${doc.chunks} sections</strong>
                        </div>
                    </div>
                </div>

                <a href="maintenance.html" class="btn btn-secondary btn-pill" style="width: 100%; justify-content: center;">
                    Consult in AI Chatbot →
                </a>
            </div>
        `;
    });

    grid.innerHTML = html;
}

async function handleDocumentUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById("pdf-upload-input");
    const uploadBtn = document.getElementById("upload-submit-btn");
    const feedbackBox = document.getElementById("upload-feedback");

    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        showFeedback("Please select a PDF file first.", "warning");
        return;
    }

    const file = fileInput.files[0];
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        showFeedback("Only PDF documents (.pdf) are allowed.", "danger");
        return;
    }

    if (file.size > 30 * 1024 * 1024) {
        showFeedback("File size exceeds 30 MB limit.", "danger");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    uploadBtn.disabled = true;
    uploadBtn.innerHTML = "<span>Uploading & Indexing with RAG...</span>";
    showFeedback("Extracting technical text and updating TF-IDF vector index. Please wait...", "info");

    try {
        const response = await fetch("/api/upload-document", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `Server error: ${response.status}`);
        }

        showFeedback(`✔ ${data.message}! Added ${data.chunks_indexed} searchable chunks to knowledge base.`, "success");
        fileInput.value = "";
        const labelEl = document.getElementById("selected-file-label");
        if (labelEl) labelEl.textContent = "Drop a PDF manual here or click to browse";

        // Refresh documents list
        await loadDocuments();

    } catch (err) {
        console.error("Upload error:", err);
        showFeedback(`Upload failed: ${err.message}`, "danger");
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = "<span>Upload & Index Document</span>";
    }
}

function showFeedback(message, type) {
    const feedbackBox = document.getElementById("upload-feedback");
    if (!feedbackBox) return;

    feedbackBox.style.display = "block";
    feedbackBox.textContent = message;

    if (type === "success") {
        feedbackBox.style.background = "var(--success-bg)";
        feedbackBox.style.borderColor = "var(--success)";
        feedbackBox.style.color = "var(--success)";
    } else if (type === "danger") {
        feedbackBox.style.background = "var(--danger-bg)";
        feedbackBox.style.borderColor = "var(--danger)";
        feedbackBox.style.color = "var(--danger)";
    } else if (type === "warning") {
        feedbackBox.style.background = "var(--warning-bg)";
        feedbackBox.style.borderColor = "var(--warning)";
        feedbackBox.style.color = "var(--warning)";
    } else {
        feedbackBox.style.background = "rgba(0, 210, 255, 0.08)";
        feedbackBox.style.borderColor = "var(--border-active)";
        feedbackBox.style.color = "var(--accent-cyan)";
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
}
