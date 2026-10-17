const FAULT_API_URL = (window.location.protocol.startsWith("http") && window.location.port === "8000")
    ? "/predict-fault"
    : "http://127.0.0.1:8000/predict-fault";

const analyzeBtn = document.getElementById("analyze-btn");
const form = document.getElementById("faultForm");
const resultBox = document.getElementById("fault-result") || document.getElementById("faultResult");
const probabilitiesSection = document.getElementById("probabilities");

const faultTitles = {
    "LG": "Single Line-to-Ground Fault",
    "LL": "Line-to-Line Fault",
    "LLG": "Double Line-to-Ground Fault",
    "LLL": "Three-Phase Symmetrical Fault",
    "LLLG": "Three-Phase-to-Ground Fault",
    "Normal": "Healthy / Normal Substation Operation"
};

const faultDescriptions = {
    "LG": "Single line-to-ground fault detected. Phase voltage collapsed with abnormal current in the affected line. Recommend checking grounding transformer and feeder protection relays.",
    "LL": "Line-to-line fault detected between two phases. High phase current with phase angle shift observed. Recommend inspecting phase conductors and busbar insulators.",
    "LLG": "Double line-to-ground fault detected involving two phases and earth. Severe current imbalance detected. Immediate trip verification and protective breaker check required.",
    "LLL": "Three-phase symmetrical fault detected across all three phases. Severe heavy fault condition. High prospective short-circuit current.",
    "LLLG": "Three-phase-to-ground fault detected involving all three phases and earth. Maximum severity condition requiring instantaneous breaker trip and isolation.",
    "Normal": "All three phase currents and voltages are balanced and within normal operating parameters. No fault condition detected."
};

const PRESET_CASES = {
    "Normal": { Ia: -35.89, Ib: -1.18, Ic: 33.75, Va: 0.46, Vb: -0.54, Vc: 0.07 },
    "LG":     { Ia: 858.35, Ib: 41.26, Ic: 12.17, Va: 0.02, Vb: -0.32, Vc: 0.30 },
    "LL":     { Ia: 47.49, Ib: -168.61, Ic: 123.94, Va: 0.49, Vb: 0.01, Vc: -0.50 },
    "LLG":    { Ia: 119.99, Ib: 695.35, Ic: 57.51, Va: 0.04, Vb: -0.27, Vc: 0.23 },
    "LLL":    { Ia: 733.24, Ib: -793.63, Ic: 62.38, Va: -0.01, Vb: -0.03, Vc: 0.04 },
    "LLLG":   { Ia: 881.61, Ib: -511.95, Ic: -369.65, Va: 0.02, Vb: -0.04, Vc: 0.03 }
};

window.loadPreset = function(presetKey) {
    const data = PRESET_CASES[presetKey];
    if (!data) return;
    document.getElementById("Ia").value = data.Ia;
    document.getElementById("Ib").value = data.Ib;
    document.getElementById("Ic").value = data.Ic;
    document.getElementById("Va").value = data.Va;
    document.getElementById("Vb").value = data.Vb;
    document.getElementById("Vc").value = data.Vc;
    performFaultAnalysis();
};

async function performFaultAnalysis() {
    const IaVal = document.getElementById("Ia")?.value.trim();
    const IbVal = document.getElementById("Ib")?.value.trim();
    const IcVal = document.getElementById("Ic")?.value.trim();
    const VaVal = document.getElementById("Va")?.value.trim();
    const VbVal = document.getElementById("Vb")?.value.trim();
    const VcVal = document.getElementById("Vc")?.value.trim();

    if (!IaVal || !IbVal || !IcVal || !VaVal || !VbVal || !VcVal) {
        if (resultBox) {
            resultBox.innerHTML = `
                <div class="result-placeholder" style="text-align: center; padding: 22px;">
                    <div class="result-icon" style="color: #ffd166; background: rgba(255, 209, 102, 0.1);">⚠</div>
                    <h3 style="color: #ffd166;">Missing Measurements</h3>
                    <p style="color: #9b9ba3;">Please enter all six parameters (Ia, Ib, Ic, Va, Vb, Vc) or click one of the preset sample buttons below.</p>
                </div>
            `;
        }
        return;
    }

    const body = {
        Ia: parseFloat(IaVal),
        Ib: parseFloat(IbVal),
        Ic: parseFloat(IcVal),
        Va: parseFloat(VaVal),
        Vb: parseFloat(VbVal),
        Vc: parseFloat(VcVal)
    };

    if (Object.values(body).some(v => isNaN(v))) {
        if (resultBox) {
            resultBox.innerHTML = `
                <div class="result-placeholder" style="text-align: center; padding: 22px;">
                    <div class="result-icon" style="color: #ff6b6b; background: rgba(255, 107, 107, 0.1);">⚠</div>
                    <h3 style="color: #ff6b6b;">Invalid Input</h3>
                    <p style="color: #9b9ba3;">Please enter valid numerical values for all current and voltage measurements.</p>
                </div>
            `;
        }
        return;
    }

    const button = analyzeBtn || (form ? form.querySelector("button[type='submit']") : null);

    if (button) {
        button.disabled = true;
        button.innerHTML = "<span>Analyzing with ML model...</span>";
    }

    if (resultBox) {
        resultBox.innerHTML = `
            <div class="result-placeholder" style="text-align: center; padding: 25px;">
                <div class="result-icon" style="animation: pulse 1s infinite;">⚡</div>
                <h3>Evaluating measurements...</h3>
                <p>Running the trained Random Forest classifier against electrical features.</p>
            </div>
        `;
    }

    try {
        const response = await fetch(FAULT_API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            throw new Error(`Server returned HTTP ${response.status}`);
        }

        const data = await response.json();
        const predictedClass = data.predicted_fault;
        const probabilities = data.probabilities || {};
        const highestProb = probabilities[predictedClass] || 0;
        const title = faultTitles[predictedClass] || predictedClass;
        const description = faultDescriptions[predictedClass] ||
            `The trained Random Forest model classified the measurements as ${predictedClass}.`;

        if (resultBox) {
            resultBox.innerHTML = `
                <div class="result-placeholder" style="text-align: left; padding: 22px 24px; width: 100%; box-sizing: border-box;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                        <span class="section-label" style="margin: 0; color: #b9ff5c; font-size: 11px; font-weight: 700; letter-spacing: 0.12em;">CLASSIFICATION RESULT</span>
                        <span style="font-size: 11px; padding: 4px 10px; border-radius: 999px; background: rgba(185, 255, 92, 0.12); border: 1px solid rgba(185, 255, 92, 0.25); color: #b9ff5c; font-weight: 700;">
                            Confidence: ${(highestProb * 100).toFixed(1)}%
                        </span>
                    </div>
                    <div style="font-size: 40px; font-weight: 800; color: #ffffff; letter-spacing: -0.02em; line-height: 1.1; margin: 4px 0 6px;">
                        ${predictedClass}
                    </div>
                    <div style="color: #b9ff5c; font-size: 14px; font-weight: 600; margin-bottom: 8px;">
                        ${title}
                    </div>
                    <p style="margin: 0; color: #9b9ba3; font-size: 13px; line-height: 1.6;">
                        ${description}
                    </p>
                </div>
            `;
        }

        if (probabilitiesSection && Object.keys(probabilities).length > 0) {
            const faultOrder = ["LG", "LL", "LLG", "LLL", "LLLG", "Normal"];
            let html = "";
            for (const fault of faultOrder) {
                const prob = probabilities[fault] !== undefined ? probabilities[fault] : 0;
                const percentage = (prob * 100).toFixed(1);
                const isWinner = (fault === predictedClass);
                html += `
                    <div class="probability-row" style="${isWinner ? 'background: rgba(185, 255, 92, 0.06); border-radius: 8px; padding: 2px 6px;' : ''}">
                        <div class="probability-label" style="${isWinner ? 'color: #b9ff5c; font-weight: 700;' : ''}">${fault}</div>
                        <div class="probability-bar">
                            <div class="probability-fill" style="width: ${percentage}%; background: ${isWinner ? '#b9ff5c' : 'rgba(255, 255, 255, 0.25)'};"></div>
                        </div>
                        <div class="probability-value" style="${isWinner ? 'color: #b9ff5c; font-weight: 700;' : ''}">${percentage}%</div>
                    </div>
                `;
            }
            probabilitiesSection.innerHTML = html;
        }

    } catch (error) {
        console.error("Fault prediction error:", error);
        if (resultBox) {
            resultBox.innerHTML = `
                <div class="result-placeholder" style="text-align: center; padding: 22px;">
                    <div class="result-icon" style="color: #ff6b6b; background: rgba(255, 107, 107, 0.1);">⚠</div>
                    <h3 style="color: #ff6b6b;">Prediction Unavailable</h3>
                    <p style="color: #9b9ba3;">Could not connect to the FastAPI prediction service (${error.message}). Please ensure the backend server is running.</p>
                </div>
            `;
        }
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = "<span>Analyze Fault</span><span class='button-arrow'>→</span>";
        }
    }
}

document.addEventListener("DOMContentLoaded", function() {
    if (analyzeBtn) {
        analyzeBtn.addEventListener("click", performFaultAnalysis);
    }
    if (form) {
        form.addEventListener("submit", function(e) {
            e.preventDefault();
            performFaultAnalysis();
        });
    }
    ["Ia", "Ib", "Ic", "Va", "Vb", "Vc"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener("keydown", function(e) {
                if (e.key === "Enter") {
                    e.preventDefault();
                    performFaultAnalysis();
                }
            });
        }
    });
});