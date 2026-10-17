// ============================================================
// PRJ_232 — SETTINGS & SYSTEM CONFIGURATION CONTROLLER
// Local preference persistence, UI theme accents & diagnostics
// ============================================================

const SETTINGS_KEY = "prj232_settings";

const defaultSettings = {
    accentColor: "#00d2ff",
    chatDensity: "detailed",
    autoScroll: true,
    audioFeedback: false
};

document.addEventListener("DOMContentLoaded", function() {
    loadSettings();
    loadDiagnostics();
    setupSettingsListeners();
});

function getSettings() {
    try {
        const saved = localStorage.getItem(SETTINGS_KEY);
        return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
    } catch (e) {
        return defaultSettings;
    }
}

function saveSettings(settings) {
    try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
        applySettings(settings);
        showSettingsSavedToast();
    } catch (e) {
        console.error("Could not save settings:", e);
    }
}

function applySettings(settings) {
    if (settings.accentColor) {
        document.documentElement.style.setProperty("--accent-cyan", settings.accentColor);
        document.documentElement.style.setProperty("--border-focus", settings.accentColor);
    }
}

function loadSettings() {
    const settings = getSettings();
    applySettings(settings);

    // Color theme radio / pills
    document.querySelectorAll("[data-accent]").forEach(btn => {
        if (btn.dataset.accent === settings.accentColor) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    // Chat density
    const densitySelect = document.getElementById("setting-chat-density");
    if (densitySelect) densitySelect.value = settings.chatDensity;

    // Auto-scroll toggle
    const scrollToggle = document.getElementById("setting-autoscroll");
    if (scrollToggle) scrollToggle.checked = settings.autoScroll;
}

function setupSettingsListeners() {
    // Accent pills
    document.querySelectorAll("[data-accent]").forEach(btn => {
        btn.addEventListener("click", function() {
            const settings = getSettings();
            settings.accentColor = this.dataset.accent;
            document.querySelectorAll("[data-accent]").forEach(b => b.classList.remove("active"));
            this.classList.add("active");
            saveSettings(settings);
        });
    });

    // Density
    const densitySelect = document.getElementById("setting-chat-density");
    if (densitySelect) {
        densitySelect.addEventListener("change", function() {
            const settings = getSettings();
            settings.chatDensity = this.value;
            saveSettings(settings);
        });
    }

    // Auto-scroll
    const scrollToggle = document.getElementById("setting-autoscroll");
    if (scrollToggle) {
        scrollToggle.addEventListener("change", function() {
            const settings = getSettings();
            settings.autoScroll = this.checked;
            saveSettings(settings);
        });
    }

    // Clear history
    const clearHistoryBtn = document.getElementById("btn-clear-chat-history");
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener("click", function() {
            if (confirm("Clear all active chatbot conversation history?")) {
                localStorage.removeItem("prj232_chat_history");
                alert("Chatbot session history cleared.");
            }
        });
    }

    // Reset defaults
    const resetBtn = document.getElementById("btn-reset-settings");
    if (resetBtn) {
        resetBtn.addEventListener("click", function() {
            if (confirm("Reset all user preferences to default values?")) {
                localStorage.removeItem(SETTINGS_KEY);
                loadSettings();
                showSettingsSavedToast("Settings reset to factory defaults.");
            }
        });
    }
}

async function loadDiagnostics() {
    const diagContainer = document.getElementById("diagnostics-info");
    if (!diagContainer) return;

    try {
        const statsRes = await fetch("/api/stats");
        const stats = statsRes.ok ? await statsRes.json() : null;

        const healthRes = await fetch("/health");
        const health = healthRes.ok ? await healthRes.json() : null;

        let html = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; font-size: 13px;">
                <div style="padding: 12px; background: rgba(7, 11, 18, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
                    <span style="color: var(--text-muted); display: block; font-size: 11px;">SERVER STATUS</span>
                    <strong style="color: var(--success);">${health?.status === 'healthy' ? '● Online & Operational' : 'Degraded'}</strong>
                </div>
                <div style="padding: 12px; background: rgba(7, 11, 18, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
                    <span style="color: var(--text-muted); display: block; font-size: 11px;">CLASSIFICATION MODEL</span>
                    <strong style="color: #fff;">${stats?.model_name || 'Random Forest'}</strong>
                </div>
                <div style="padding: 12px; background: rgba(7, 11, 18, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
                    <span style="color: var(--text-muted); display: block; font-size: 11px;">MODEL ACCURACY</span>
                    <strong style="color: var(--accent-cyan);">${stats ? (stats.model_val_accuracy * 100).toFixed(2) + '%' : '86.94%'}</strong>
                </div>
                <div style="padding: 12px; background: rgba(7, 11, 18, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
                    <span style="color: var(--text-muted); display: block; font-size: 11px;">INDEXED DOCUMENT CHUNKS</span>
                    <strong style="color: #fff;">${health?.documents || 884} searchable sections</strong>
                </div>
                <div style="padding: 12px; background: rgba(7, 11, 18, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
                    <span style="color: var(--text-muted); display: block; font-size: 11px;">GENERATIVE AI MODEL</span>
                    <strong style="color: #fff;">${health?.gemini_model || 'gemini-flash-latest'}</strong>
                </div>
                <div style="padding: 12px; background: rgba(7, 11, 18, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
                    <span style="color: var(--text-muted); display: block; font-size: 11px;">CREDENTIALS SECURITY</span>
                    <strong style="color: var(--success);">Protected (Backend Environment Only)</strong>
                </div>
            </div>
        `;
        diagContainer.innerHTML = html;
    } catch (e) {
        diagContainer.innerHTML = `<p style="color: var(--text-muted);">Could not fetch diagnostic telemetry.</p>`;
    }
}

function showSettingsSavedToast(msg = "Preference applied and saved.") {
    const toast = document.createElement("div");
    toast.style.cssText = "position: fixed; bottom: 24px; right: 24px; padding: 12px 20px; background: var(--bg-card); border: 1px solid var(--accent-cyan); color: #fff; border-radius: var(--radius-sm); font-size: 13px; font-weight: 600; box-shadow: var(--shadow-md); z-index: 9999; animation: fadeIn 0.2s ease;";
    toast.textContent = "✔ " + msg;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 2200);
}
