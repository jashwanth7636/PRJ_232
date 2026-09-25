const FAULT_API_URL = "http://127.0.0.1:8000/predict-fault";

const form = document.getElementById("faultForm");
const resultBox = document.getElementById("faultResult");


const faultDescriptions = {

    "LG": "Single line-to-ground fault detected based on the supplied three-phase measurements.",

    "LL": "Line-to-line fault detected between two phases.",

    "LLG": "Double line-to-ground fault detected involving two phases and ground.",

    "LLL": "Three-phase fault detected involving all three phases.",

    "LLLG": "Three-phase-to-ground fault detected involving all three phases and ground.",

    "Normal": "No fault condition was classified for the supplied measurements."

};


if (form) {

    form.addEventListener("submit", async function(event) {

        event.preventDefault();

        const button =
            form.querySelector("button[type='submit']");


        if (button) {

            button.disabled = true;

            button.innerHTML =
                "<span>Analyzing...</span>";
        }


        resultBox.innerHTML = `
            <div class="result-placeholder">

                <div class="placeholder-icon">
                    ⚡
                </div>

                <h3>
                    Analyzing measurements...
                </h3>

                <p>
                    Running the trained Random Forest model.
                </p>

            </div>
        `;


        try {

            const body = {

                Ia: parseFloat(
                    document.getElementById("Ia").value
                ),

                Ib: parseFloat(
                    document.getElementById("Ib").value
                ),

                Ic: parseFloat(
                    document.getElementById("Ic").value
                ),

                Va: parseFloat(
                    document.getElementById("Va").value
                ),

                Vb: parseFloat(
                    document.getElementById("Vb").value
                ),

                Vc: parseFloat(
                    document.getElementById("Vc").value
                )

            };


            const response = await fetch(
                FAULT_API_URL, {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(body)
                }
            );


            if (!response.ok) {

                throw new Error(
                    `Server error: ${response.status}`
                );

            }


            const data =
                await response.json();


            let probabilityHTML = "";


            for (
                const [
                    fault,
                    probability
                ] of Object.entries(data.probabilities)
            ) {

                const percentage =
                    probability * 100;


                probabilityHTML += `

                    <div class="probability-row">

                        <span>
                            ${fault}
                        </span>

                        <div class="probability-bar">

                            <div
                                class="probability-fill"
                                style="width:${percentage}%"
                            ></div>

                        </div>

                        <span>
                            ${percentage.toFixed(2)}%
                        </span>

                    </div>

                `;

            }


            const description =
                faultDescriptions[
                    data.predicted_fault
                ] ||
                "The trained model classified the supplied measurements as " +
                data.predicted_fault + ".";


            resultBox.innerHTML = `

                <div class="prediction-success">

                    <div class="prediction-label">
                        PREDICTED FAULT
                    </div>

                    <div class="prediction-value">
                        ${data.predicted_fault}
                    </div>

                    <p class="prediction-description">
                        ${description}
                    </p>

                    <div class="probability-title">
                        Model Probabilities
                    </div>

                    <div class="probability-list">

                        ${probabilityHTML}

                    </div>

                </div>

            `;


        } catch (error) {

            console.error(error);


            resultBox.innerHTML = `

                <div class="prediction-error">

                    <h3>
                        Prediction unavailable
                    </h3>

                    <p>
                        Could not connect to the
                        FastAPI fault prediction service.
                    </p>

                </div>

            `;

        }


        if (button) {

            button.disabled = false;

            button.innerHTML = `
                <span>
                    Analyze Fault
                </span>

                <span class="button-arrow">
                    →
                </span>
            `;

        }

    });

}