// ============================================================
// PRJ_232 — MAINTENANCE CHECKLISTS CONTROLLER
// Interactive task completion, progress calculation & persistence
// ============================================================

const STORAGE_KEY = "prj232_checklist_state";
let checklistsData = [];

document.addEventListener("DOMContentLoaded", async function() {
    await loadChecklists();
});

async function loadChecklists() {
    const container = document.getElementById("checklists-container");
    if (!container) return;

    try {
        const res = await fetch("/api/checklists");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        checklistsData = await res.json();
        renderChecklists();
        updateProgress();
    } catch (err) {
        console.error("Could not load checklists:", err);
        container.innerHTML = `<p style="color: var(--danger); text-align: center;">Failed to load checklists from server.</p>`;
    }
}

function getStoredState() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) : {};
    } catch (e) {
        return {};
    }
}

function saveStoredState(state) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
        console.error("Could not save to localStorage:", e);
    }
}

function renderChecklists() {
    const container = document.getElementById("checklists-container");
    if (!container) return;

    const state = getStoredState();
    let html = "";

    checklistsData.forEach(group => {
        let tasksHtml = "";
        group.tasks.forEach(task => {
            const isChecked = !!state[task.id];
            tasksHtml += `
                <div class="task-item ${isChecked ? 'completed' : ''}" onclick="toggleTask('${task.id}')">
                    <div class="task-checkbox ${isChecked ? 'checked' : ''}">
                        ${isChecked ? '✓' : ''}
                    </div>
                    <div class="task-text">${task.text}</div>
                    ${task.critical ? '<span class="task-tag-critical">CRITICAL</span>' : ''}
                </div>
            `;
        });

        html += `
            <div class="checklist-group" id="group-${group.id}">
                <div class="checklist-header">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--accent-cyan); letter-spacing: 0.08em; text-transform: uppercase;">
                            STANDARD: ${group.standard} • FREQUENCY: ${group.frequency}
                        </div>
                        <h2 style="font-size: 18px; color: #fff; margin-top: 4px;">${group.title}</h2>
                    </div>
                    <div id="badge-${group.id}" style="font-size: 12px; font-weight: 700; color: var(--text-secondary); background: rgba(255,255,255,0.05); padding: 4px 10px; border-radius: var(--radius-pill); border: 1px solid var(--border-subtle);">
                        0% Complete
                    </div>
                </div>
                <div class="tasks-list">
                    ${tasksHtml}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

window.toggleTask = function(taskId) {
    const state = getStoredState();
    state[taskId] = !state[taskId];
    saveStoredState(state);
    renderChecklists();
    updateProgress();
};

function updateProgress() {
    const state = getStoredState();
    let totalTasks = 0;
    let completedTasks = 0;

    checklistsData.forEach(group => {
        let groupTotal = group.tasks.length;
        let groupCompleted = 0;

        group.tasks.forEach(task => {
            totalTasks++;
            if (state[task.id]) {
                groupCompleted++;
                completedTasks++;
            }
        });

        const groupPct = groupTotal > 0 ? Math.round((groupCompleted / groupTotal) * 100) : 0;
        const badge = document.getElementById(`badge-${group.id}`);
        if (badge) {
            badge.textContent = `${groupPct}% Complete`;
            if (groupPct === 100) {
                badge.style.color = "var(--success)";
                badge.style.borderColor = "var(--success)";
                badge.style.background = "var(--success-bg)";
            } else {
                badge.style.color = "var(--text-secondary)";
                badge.style.borderColor = "var(--border-subtle)";
                badge.style.background = "rgba(255,255,255,0.05)";
            }
        }
    });

    const overallPct = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
    const progressText = document.getElementById("overall-progress-text");
    if (progressText) progressText.textContent = `${overallPct}%`;

    const progressBar = document.getElementById("overall-progress-bar");
    if (progressBar) progressBar.style.width = `${overallPct}%`;

    const summaryText = document.getElementById("overall-progress-summary");
    if (summaryText) summaryText.textContent = `${completedTasks} of ${totalTasks} procedures verified`;
}

window.resetChecklists = function() {
    if (confirm("Are you sure you want to reset all checklist progress? This action cannot be undone.")) {
        localStorage.removeItem(STORAGE_KEY);
        renderChecklists();
        updateProgress();
    }
};

window.printChecklists = function() {
    window.print();
};
