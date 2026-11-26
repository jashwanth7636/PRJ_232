// ============================================================
// PRJ_232 — ELECTRICAL FAULT ANALYSIS CONTROLLER
// Real-time inference via trained Random Forest classifier
// ============================================================

const FAULT_API_URL = (window.location.protocol.startsWith("http") && window.location.port === "8000")
    ? "/predict-fault"
    : "http://127.0.0.1:8000/predict-fault";

const faultDetails = {
    "LG": {
        title: "Single Line-to-Ground Fault",
        description: "A single phase has short-circuited to earth. Typical causes include insulation breakdown, lightning strikes, or tree branch contact on transmission conductors.",
        recommendations: "1. Trip affected phase relay and verify breaker opening.\n2. Inspect surge arresters and ground transformer grounding resistor (NGR).\n3. Test line insulation resistance with 5kV Megger before reclosing.",
        severity: "Moderate to High",
        severityClass: "warning"
    },
    "LL": {
        title: "Line-to-Line Fault",
        description: "Two phases have shorted together without ground involvement. High prospective line currents with 120° phase displacement shift observed.",
        recommendations: "1. Verify overcurrent and distance protection zone 1 reach.\n2. Inspect phase-to-phase clearances on overhead busbars and disconnect switches.\n3. Perform micro-ohmmeter contact resistance check across breaker poles.",
        severity: "High",
        severityClass: "warning"
    },
    "LLG": {
        title: "Double Line-to-Ground Fault",
        description: "Two phases have simultaneously faulted to ground. Severe current asymmetry and significant ground-return fault current detected.",
        recommendations: "1. Instantaneous trip isolation required.\n2. Inspect transformer neutral bushing and grounding grid conductor joints.\n3. Check differential relay trip matrix.",
        severity: "Critical",
        severityClass: "danger"
    },
    "LLL": {
        title: "Three-Phase Symmetrical Fault",
        description: "All three phases are short-circuited symmetrically. Highest theoretical short-circuit current magnitude requiring maximum breaking capacity.",
        recommendations: "1. Immediate busbar and transformer protection trip.\n2. Inspect busbar insulators for flashover or mechanical stress displacement.\n3. Conduct dissolved gas analysis (DGA) on power transformer oil.",
        severity: "Severe",
        severityClass: "danger"
    },
    "LLLG": {
        title: "Three-Phase-to-Ground Fault",
        description: "All three phases shorted to earth simultaneously. Maximum fault energy dissipation involving all phases and station ground grid.",
        recommendations: "1. Complete feeder bay lockout and station perimeter inspection.\n2. Verify station earth mat potential rise and step/touch potentials.\n3. Comprehensive dielectric withstand testing before restoring power.",
        severity: "Maximum",
        severityClass: "danger"
    },
    "Normal": {
        title: "Balanced Normal Operating Condition",
        description: "All three phase currents and voltages are balanced and conform to permissible operating tolerances. No electrical fault detected.",
        recommendations: "Continue standard operational monitoring and regular scheduled thermographic scans.",
        severity: "Nominal",
        severityClass: "success"
    }
};

// Ground-truth sample measurements from test dataset
const PRESET_CASES = {
    "Normal": { Ia: -35.89, Ib: -1.18, Ic: 33.75, Va: 0.46, Vb: -0.54, Vc: 0.07 },
    "LG":     { Ia: 858.35, Ib: 41.26, Ic: 12.17, Va: 0.02, Vb: -0.32, Vc: 0.30 },
    "LL":     { Ia: 47.49, Ib: -168.61, Ic: 123.94, Va: 0.49, Vb: 0.01, Vc: -0.50 },
    "LLG":    { Ia: 119.99, Ib: 695.35, Ic: 57.51, Va: 0.04, Vb: -0.27, Vc: 0.23 },
    "LLL":    { Ia: 733.24, Ib: -793.63, Ic: 62.38, Va: -0.01, Vb: -0.03, Vc: 0.04 },
    "LLLG":   { Ia: 881.61, Ib: -511.95, Ic: -369.65, Va: 0.02, Vb: -0.04, Vc: 0.03 }
};

document.addEventListener("DOMContentLoaded", function() {
    const analyzeBtn = document.getElementById("analyze-btn");
    if (analyzeBtn) {
        analyzeBtn.addEventListener("click", performFaultAnalysis);
    }

    const resetBtn = document.getElementById("reset-btn");
    if (resetBtn) {
        resetBtn.addEventListener("click", resetFaultForm);
    }

    ["Ia", "Ib", "Ic", "Va", "Vb", "Vc"].forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener("keydown", function(e) {
                if (e.key === "Enter") {
                    e.preventDefault();
                    performFaultAnalysis();
                }
            });
        }
    });
});

window.loadPreset = function(presetKey) {
    const data = PRESET_CASES[presetKey];
    if (!data) return;

    document.getElementById("Ia").value = data.Ia;
    document.getElementById("Ib").value = data.Ib;
    document.getElementById("Ic").value = data.Ic;
    document.getElementById("Va").value = data.Va;
    document.getElementById("Vb").value = data.Vb;
    document.getElementById("Vc").value = data.Vc;

    clearFieldErrors();
    performFaultAnalysis();
};

function clearFieldErrors() {
    document.querySelectorAll(".field-error").forEach(el => el.remove());
    document.querySelectorAll(".form-input").forEach(el => el.style.borderColor = "");
}

function resetFaultForm() {
    ["Ia", "Ib", "Ic", "Va", "Vb", "Vc"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = "";
    });
    clearFieldErrors();

    const resultBox = document.getElementById("fault-result");
    if (resultBox) {
        resultBox.innerHTML = `
            <div style="text-align: center; padding: 40px 20px;">
                <div style="width: 48px; height: 48px; margin: 0 auto 14px; border-radius: 12px; background: rgba(0, 210, 255, 0.08); border: 1px solid var(--border-card); display: flex; align-items: center; justify-content: center; font-size: 22px; color: var(--accent-cyan);">⚡</div>
                <h3 style="color: #fff; font-size: 16px; margin-bottom: 6px;">Awaiting Measurements</h3>
                <p style="color: var(--text-muted); font-size: 13px; max-width: 320px; margin: 0 auto;">Enter 3-phase current and voltage parameters or pick a sample preset to evaluate.</p>
            </div>
        `;
    }

    const probabilitiesSection = document.getElementById("probabilities");
    if (probabilitiesSection) {
        const faultOrder = ["LG", "LL", "LLG", "LLL", "LLLG", "Normal"];
        let html = "";
        faultOrder.forEach(f => {
            html += `
                <div class="probability-row" style="display: grid; grid-template-columns: 55px 1fr 50px; align-items: center; gap: 12px; margin-bottom: 12px; font-size: 12px;">
                    <span style="font-weight: 700; color: var(--text-secondary);">${f}</span>
                    <div style="height: 6px; border-radius: 99px; background: rgba(255,255,255,0.06); overflow: hidden;">
                        <div style="height: 100%; width: 0%; background: var(--accent-cyan); transition: width 0.4s ease;"></div>
                    </div>
                    <span style="text-align: right; color: var(--text-muted); font-family: var(--font-mono);">0.0%</span>
                </div>
            `;
        });
        probabilitiesSection.innerHTML = html;
    }
}

async function performFaultAnalysis() {
    clearFieldErrors();
    const fields = ["Ia", "Ib", "Ic", "Va", "Vb", "Vc"];
    const body = {};
    let hasError = false;

    fields.forEach(f => {
        const input = document.getElementById(f);
        const valStr = input?.value.trim();

        if (!valStr) {
            showFieldError(input, "Required");
            hasError = true;
        } else {
            const num = parseFloat(valStr);
            if (isNaN(num)) {
                showFieldError(input, "Invalid number");
                hasError = true;
            } else {
                body[f] = num;
            }
        }
    });

    if (hasError) return;

    const analyzeBtn = document.getElementById("analyze-btn");
    const resultBox = document.getElementById("fault-result");
    const probabilitiesSection = document.getElementById("probabilities");

    if (analyzeBtn) {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = "<span>Classifying with Random Forest...</span>";
    }

    if (resultBox) {
        resultBox.innerHTML = `
            <div style="text-align: center; padding: 35px 20px;">
                <div style="font-size: 28px; animation: statusPulse 1s infinite; margin-bottom: 12px;">⚡</div>
                <h3 style="color: #fff; font-size: 16px; margin-bottom: 6px;">Evaluating Sensor Parameters</h3>
                <p style="color: var(--text-muted); font-size: 13px;">Running trained model feature mapping...</p>
            </div>
        `;
    }

    try {
        const response = await fetch(FAULT_API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            throw new Error(`Server returned HTTP ${response.status}`);
        }

        const data = await response.json();
        const pred = data.predicted_fault;
        const probs = data.probabilities || {};
        const confidence = probs[pred] ? (probs[pred] * 100).toFixed(1) : "0.0";
        const details = faultDetails[pred] || {
            title: "Electrical Condition: " + pred,
            description: "Classified by trained Random Forest model.",
            recommendations: "Inspect breaker and feeder protective relays.",
            severity: "Elevated",
            severityClass: "warning"
        };

        if (resultBox) {
            const badgeBg = details.severityClass === 'success' ? 'var(--success-bg)' : (details.severityClass === 'danger' ? 'var(--danger-bg)' : 'var(--warning-bg)');
            const badgeColor = details.severityClass === 'success' ? 'var(--success)' : (details.severityClass === 'danger' ? 'var(--danger)' : 'var(--warning)');

            resultBox.innerHTML = `
                <div style="padding: 24px; text-align: left; width: 100%; box-sizing: border-box;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <span style="font-size: 11px; font-weight: 700; letter-spacing: 0.1em; color: var(--copper-primary); text-transform: uppercase;">
                            CLASSIFIED FAULT CONDITION
                        </span>
                        <span style="font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: var(--radius-pill); background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeColor};">
                            ${details.severity} Severity
                        </span>
                    </div>

                    <div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 6px;">
                        <div style="font-size: 46px; font-weight: 900; color: #fff; letter-spacing: -0.03em; font-family: var(--font-mono);">${pred}</div>
                        <div style="font-size: 16px; font-weight: 700; color: var(--copper-hover);">${details.title}</div>
                    </div>

                    <p style="color: #cbd5e1; font-size: 13.5px; line-height: 1.6; margin-bottom: 16px;">
                        ${details.description}
                    </p>

                    <div style="padding: 14px; background: rgba(7, 11, 18, 0.6); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); margin-bottom: 16px;">
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px;">RECOMMENDED ACTION</div>
                        <div style="font-size: 12.5px; color: #e2e8f0; white-space: pre-line; line-height: 1.5;">${details.recommendations}</div>
                    </div>

                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--text-muted);">
                        <span>Model Confidence: <strong style="color: #fff;">${confidence}%</strong></span>
                        <span>Model: <strong style="color: var(--copper-hover);">Random Forest (86.9% Val Acc)</strong></span>
                    </div>
                </div>
            `;
        }

        if (probabilitiesSection && Object.keys(probs).length > 0) {
            const faultOrder = ["LG", "LL", "LLG", "LLL", "LLLG", "Normal"];
            let html = "";
            faultOrder.forEach(f => {
                const p = probs[f] !== undefined ? probs[f] : 0;
                const pct = (p * 100).toFixed(1);
                const isWinner = (f === pred);
                html += `
                    <div style="display: grid; grid-template-columns: 55px 1fr 50px; align-items: center; gap: 12px; margin-bottom: 10px; font-size: 12px; ${isWinner ? 'background: rgba(245, 158, 54, 0.12); padding: 6px 10px; border-radius: var(--radius-sm); border: 1px solid rgba(245, 158, 54, 0.4);' : 'padding: 4px 6px;'}">
                        <span style="font-weight: 700; color: ${isWinner ? 'var(--copper-hover)' : 'var(--text-secondary)'}; font-family: var(--font-mono);">${f}</span>
                        <div style="height: 6px; border-radius: 99px; background: rgba(255,255,255,0.06); overflow: hidden;">
                            <div style="height: 100%; width: ${pct}%; background: ${isWinner ? 'var(--copper-gradient)' : 'rgba(255,255,255,0.2)'}; transition: width 0.5s ease;"></div>
                        </div>
                        <span style="text-align: right; font-weight: ${isWinner ? '700' : '400'}; color: ${isWinner ? 'var(--copper-hover)' : 'var(--text-muted)'}; font-family: var(--font-mono);">${pct}%</span>
                    </div>
                `;
            });
            probabilitiesSection.innerHTML = html;
        }

    } catch (err) {
        console.error("Prediction error:", err);
        if (resultBox) {
            resultBox.innerHTML = `
                <div style="text-align: center; padding: 30px 20px;">
                    <div style="font-size: 26px; color: var(--danger); margin-bottom: 10px;">⚠</div>
                    <h3 style="color: var(--danger); font-size: 15px; margin-bottom: 6px;">Prediction Service Unavailable</h3>
                    <p style="color: var(--text-muted); font-size: 12.5px;">Could not connect to FastAPI model service (${err.message}). Ensure the server is active on port 8000.</p>
                </div>
            `;
        }
    } finally {
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = "<span>Analyze Electrical Fault</span> →";
        }
    }
}

function showFieldError(inputEl, msg) {
    if (!inputEl) return;
    inputEl.style.borderColor = "var(--danger)";
    const err = document.createElement("div");
    err.className = "field-error";
    err.style.cssText = "color: var(--danger); font-size: 11px; margin-top: 4px; font-weight: 600;";
    err.textContent = msg;
    inputEl.parentNode.appendChild(err);
}