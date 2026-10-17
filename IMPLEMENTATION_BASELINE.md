# PRJ_232 — VoltSage AI
## Stage 1 Implementation Baseline & System Audit Report

**Audit Date:** October 17, 2026  
**Project ID:** PRJ_232  
**Target Identity:** VoltSage AI (AI-Powered Maintenance Chatbot for Electrical Substations)  
**Active Branch:** `feature/voltsage-ai-upgrade`  
**Baseline Git Checkpoint:** Commit `33f2e6f` | Tag: `stage1-checkpoint`  
**Execution Environment:** Windows PowerShell, Python 3.11 (`.venv`), FastAPI / Uvicorn  

---

## 1. Project Directory Structure

```
c:\Users\saigo\OneDrive\Desktop\new mini project. 7sem\
├── .env                              # Local environment variables (GEMINI_API_KEY) [Protected, not in Git]
├── .gitignore                         # Standard Python, secrets, large data ignore rules
├── requirements.txt                   # Production Python package dependencies
├── run_project.bat                    # One-click Windows CMD launcher (directory-safe)
├── test_all_endpoints.py              # Automated regression & baseline test suite
├── vercel.json                        # Vercel deployment configuration
├── IMPLEMENTATION_BASELINE.md         # This audit baseline document
│
├── api/
│   └── index.py                       # Vercel serverless entrypoint importing backend.main:app
│
├── backend/
│   ├── main.py                        # Primary FastAPI application entrypoint & static mount
│   ├── routes/                        # Route stubs for future modularity
│   └── schemas/                       # Schema stubs for future modularity
│
├── data/
│   ├── raw/
│   │   ├── classData.csv              # Raw electrical fault dataset
│   │   └── detect_dataset.csv         # Raw electrical detection telemetry
│   ├── splits/
│   │   ├── train.csv                  # 70% stratified training split
│   │   ├── validation.csv             # 15% validation split
│   │   └── test.csv                   # 15% test split
│   └── processed/
│       ├── clean_fault_dataset.csv    # Cleaned fault dataset with standardized columns
│       ├── document_chunks.json       # 884 searchable text chunks extracted from manuals
│       ├── Circuit Breaker Maintenance Guide 0002.txt
│       ├── Electrical Substation Maintenance Information 0003.txt
│       ├── ETC Manual for Flat wall &amp; Corrugated Transformer 0001.txt
│       └── all_maintenance_documents.txt
│
├── documents/                         # Authoritative source PDF manuals
│   ├── Circuit Breaker Maintenance Guide 0002.pdf
│   ├── Electrical Substation Maintenance Information 0003.pdf
│   └── ETC Manual for Flat wall &amp; Corrugated Transformer 0001.pdf
│
├── document_processing/
│   ├── extract_text.py                # PDF text extraction utility using pypdf
│   └── chunk_documents.py             # 1200-char window / 200-char overlap chunking pipeline
│
├── evaluation/
│   └── results/
│       ├── confusion_matrix.csv       # Confusion matrix from evaluation split
│       ├── final_test_results.csv     # Final test set accuracy and F1 score
│       └── model_comparison.csv       # Benchmark comparing Random Forest, XGBoost, and Logistic Regression
│
├── frontend/
│   ├── index.html                     # Main Operations Dashboard
│   ├── maintenance.html               # AI Maintenance Chatbot interface
│   ├── fault-analysis.html            # 3-Phase Electrical Fault Classifier UI
│   ├── knowledge-base.html            # Document repository and PDF uploader UI
│   ├── checklists.html                # Interactive substation maintenance checklists
│   ├── settings.html                  # User preferences and system diagnostics UI
│   ├── about.html                     # Project architecture, engineering motivation & benchmarks
│   ├── css/
│   │   ├── industrial.css             # Industrial SCADA design system (navy/charcoal/cyan)
│   │   └── style.css                  # Legacy stylesheet
│   └── js/
│       ├── dashboard.js               # Telemetry and bay status controller
│       ├── maintenance.js             # Chatbot markdown renderer and API connector
│       ├── fault-analysis.js          # Fault classifier form validation and probability gauge
│       ├── knowledge-base.js          # Search, category filter, and PDF upload controller
│       ├── checklists.js              # Checklist completion and localStorage manager
│       └── settings.js                # Accent theme switcher and diagnostic telemetry loader
│
├── ml/
│   ├── artifacts/
│   │   ├── best_fault_model.joblib    # Trained Random Forest Classifier (100 estimators)
│   │   ├── label_encoder.joblib       # Scikit-Learn LabelEncoder mapping 6 fault classes
│   │   └── scaler.joblib              # Scikit-Learn StandardScaler
│   ├── train_models.py                # Model training, hyperparameter tuning & evaluation script
│   ├── predict_fault.py               # Standalone CLI fault prediction utility
│   ├── prepare_dataset.py             # Dataset cleaning and split generation script
│   ├── analyze_dataset_structure.py   # Exploratory data analysis utility
│   ├── analyze_fault_labels.py        # Class balance audit script
│   ├── check_data_order.py            # Feature sequencing validation script
│   └── inspect_dataset.py             # Schema verification utility
│
└── retrieval/
    └── search_documents.py            # Local TF-IDF cosine similarity search utility
```

---

## 2. FastAPI Backend Architecture & API Contracts

- **Entrypoint:** `backend/main.py:app`
- **ASGI Server:** Uvicorn 0.x on `http://127.0.0.1:8000`
- **CORS Configuration:**
  - `allow_origins=["*"]`
  - `allow_credentials=False`
  - `allow_methods=["*"]`
  - `allow_headers=["*"]`
  *(Note: In Stage 3, when introducing cookie-based authentication, `allow_credentials` must be configured with explicit origins instead of wildcard `*` to adhere to security standards).*

### Existing REST Endpoint Contracts

| Method | Endpoint | Request Schema | Response Schema | Purpose |
|---|---|---|---|---|
| `GET` | `/health`, `/api/health` | None | `{"status": str, "gemini": str, "gemini_model": str, "fault_model": str, "documents": int}` | Liveness & health probe |
| `POST` | `/chat` | `{"message": str, "history": list[dict]}` | `{"answer": str, "sources": list[{"source": str, "score": float}]}` | RAG-augmented chatbot generation |
| `POST` | `/predict-fault` | `{"Ia": float, "Ib": float, "Ic": float, "Va": float, "Vb": float, "Vc": float}` | `{"predicted_fault": str, "probabilities": dict[str, float]}` | Real-time Random Forest classification |
| `GET` | `/api/documents` | None | `{"documents": list[dict], "total_documents": int, "total_chunks": int, "indexed_documents": int}` | Knowledge base document listing |
| `POST` | `/api/upload-document` | Multipart `file: UploadFile` (.pdf) | `{"status": str, "message": str, "filename": str, "chunks_indexed": int, "total_chunks": int}` | Dynamic PDF ingestion & vector reload |
| `GET` | `/api/stats` | None | Telemetry object (accuracies, monitored bays, fault classes) | Real-time SCADA dashboard statistics |
| `GET` | `/api/checklists` | None | List of checklist objects with tasks, frequencies, and standards | Standardized inspection procedures |
| `GET` | `/` | None | `frontend/index.html` (FileResponse) | Application landing page |
| `GET` | `/{page_name:path}` | None | Matching HTML/static file or HTTP 404 | Dynamic frontend page routing |

---

## 3. Machine Learning Model Specifications

- **Saved Artifact:** `ml/artifacts/best_fault_model.joblib` (RandomForestClassifier)
- **Label Encoder:** `ml/artifacts/label_encoder.joblib` (6 classes)
- **Feature Scaler:** `ml/artifacts/scaler.joblib` (StandardScaler)
- **Input Features (Exact Order):**
  1. `Ia` — Phase A Current (Amperes A)
  2. `Ib` — Phase B Current (Amperes A)
  3. `Ic` — Phase C Current (Amperes A)
  4. `Va` — Phase A Voltage (Per Unit p.u.)
  5. `Vb` — Phase B Voltage (Per Unit p.u.)
  6. `Vc` — Phase C Voltage (Per Unit p.u.)
- **Target Variable:** `Fault_Type`
- **Class Labels Mapping:**
  - `0` -> `LG` (Single Line-to-Ground Fault)
  - `1` -> `LL` (Line-to-Line Fault)
  - `2` -> `LLG` (Double Line-to-Ground Fault)
  - `3` -> `LLL` (Three-Phase Symmetrical Fault)
  - `4` -> `LLLG` (Three-Phase-to-Ground Fault)
  - `5` -> `Normal` (Balanced Operational State)
- **Empirical Evaluation Results (from `evaluation/results/`):**
  - **Random Forest (100 Trees):** Val Accuracy = **86.94%**, Test Accuracy = **85.34%**, Precision = **85.37%**, Recall = **85.34%**, F1 = **85.34%** (Deployed)
  - **XGBoost:** Accuracy = 82.78%, F1 = 82.75%
  - **Logistic Regression:** Accuracy = 35.37%, F1 = 23.35% (Underfitting)

---

## 4. Document Processing & RAG Retrieval Pipeline

- **Corpus Sources:** 3 technical substation engineering manuals located in `documents/`:
  1. `Circuit Breaker Maintenance Guide 0002.pdf` (5.44 MB)
  2. `Electrical Substation Maintenance Information 0003.pdf` (3.00 MB)
  3. `ETC Manual for Flat wall & Corrugated Transformer 0001.pdf` (6.17 MB)
- **Chunking Pipeline:**
  - Chunk Size: `1200` characters
  - Chunk Overlap: `200` characters
  - Minimum Chunk Length: `250` characters (noise filtering)
  - Output Storage: `data/processed/document_chunks.json` (884 indexed segments)
- **Vector Search Engine:**
  - `scikit-learn` `TfidfVectorizer` (English stop words, n-gram range (1, 2), max_features=30000)
  - Cosine similarity matching (`cosine_similarity`)
  - Top-K: Retrieves top-3 most relevant chunks per query
- **Dynamic Ingestion:** `POST /api/upload-document` accepts `.pdf`, extracts text with `pypdf`, chunks and appends to `document_chunks.json`, and triggers `reload_document_index()` in memory without restarting the FastAPI server.

---

## 5. Generative AI (Gemini) Configuration

- **SDK:** `google-genai` (Official modern Google GenAI Python SDK)
- **Client Initialization:** `genai.Client(api_key=GEMINI_API_KEY)` from `.env`
- **Default Model:** `gemini-flash-latest` (overridable via `GEMINI_MODEL`)
- **Generation Parameters:**
  - `temperature = 0.2` (strict engineering grounding)
  - `max_output_tokens = 2500` (provides headroom for internal reasoning thoughts and complete answers)
  - `system_instruction`: Strict engineering role mandating grounded procedural guidelines, PPE safety notices, and disallowing hallucinated standards.
- **Error Boundary & Graceful Degradation:**
  - If Gemini API returns a rate limit (HTTP 429) or connection error, the backend catches the exception and synthesizes a direct response using the retrieved technical documentation snippets rather than crashing or showing a blank bubble.

---

## 6. Frontend Architecture & Design System

- **Visual Theme:** Industrial SCADA Engineering Design System (`frontend/css/industrial.css`)
  - Background Base: `#070b12`, Surface: `#0c1220`, Card: `#111a2e`
  - Accents: Electric Cyan (`#00d2ff`), Royal Blue (`#0066ff`), Emerald Success (`#00f59b`)
  - Typography: System sans-serif + monospace for sensor parameters
- **Pages Available (7 pages):**
  1. `index.html` — Operations Dashboard with live telemetry
  2. `maintenance.html` — AI Maintenance Copilot with citations and suggested prompt pills
  3. `fault-analysis.html` — Sensor input form with ground truth presets and posterior probability distribution
  4. `knowledge-base.html` — Searchable document catalog and drag-and-drop PDF upload
  5. `checklists.html` — Interactive substation maintenance verification checklists with `localStorage` persistence
  6. `settings.html` — Accent color selector, response density, and backend diagnostics
  7. `about.html` — Final-year B.Tech capstone documentation, ML comparison table, and standards
- **Active Navigation & Controls:**
  - Shared industrial top navbar with live heartbeat indicator (`.status-dot`)
  - Shared engineering footer with system telemetry and standards references
  - Zero dead buttons: every button has an active JavaScript event listener or an explicit status handler.

---

## 7. Baseline Verification Test Results

Executed automated test suite `test_all_endpoints.py` at `2026-10-17 13:11:58`:

```
======================================================================
PRJ_232: END-TO-END AUTOMATED VERIFICATION SUITE
======================================================================

1. Verifying HTML Pages...
  [PASS] Main Dashboard (Root) (/) -> HTTP 200, 16058 bytes
  [PASS] Main Dashboard (Explicit) (/index.html) -> HTTP 200, 16058 bytes
  [PASS] AI Maintenance Chatbot (/maintenance.html) -> HTTP 200, 14064 bytes
  [PASS] Electrical Fault Analysis (/fault-analysis.html) -> HTTP 200, 20028 bytes
  [PASS] Knowledge Base & Upload (/knowledge-base.html) -> HTTP 200, 12235 bytes
  [PASS] Maintenance Checklists (/checklists.html) -> HTTP 200, 7927 bytes
  [PASS] Settings & Diagnostics (/settings.html) -> HTTP 200, 11289 bytes
  [PASS] Project Information & ML Architecture (/about.html) -> HTTP 200, 21454 bytes

2. Verifying Static CSS & JS Assets...
  [PASS] Industrial SCADA CSS Design System (/css/industrial.css) -> HTTP 200, 20569 bytes
  [PASS] Dashboard Controller (/js/dashboard.js) -> HTTP 200, 4372 bytes
  [PASS] Maintenance Chat Controller (/js/maintenance.js) -> HTTP 200, 8469 bytes
  [PASS] Fault Analysis Controller (/js/fault-analysis.js) -> HTTP 200, 15356 bytes
  [PASS] Knowledge Base Controller (/js/knowledge-base.js) -> HTTP 200, 10538 bytes
  [PASS] Checklists Controller (/js/checklists.js) -> HTTP 200, 5463 bytes
  [PASS] Settings Controller (/js/settings.js) -> HTTP 200, 7909 bytes

3. Verifying REST API Endpoints...
  [PASS] Health Check API (/health) -> HTTP 200, 117 bytes
  [PASS] Telemetry & ML Statistics API (/api/stats) -> HTTP 200, 813 bytes
  [PASS] Document Repository API (/api/documents) -> HTTP 200, 804 bytes
  [PASS] Maintenance Checklists API (/api/checklists) -> HTTP 200, 3539 bytes

4. Verifying Machine Learning Fault Classifier (/predict-fault)...
  [PASS] Fault Prediction for Normal (/predict-fault) -> HTTP 200, Predicted: Normal, Probabilities calculated
  [PASS] Fault Prediction for LG (/predict-fault) -> HTTP 200, Predicted: LG, Probabilities calculated
  [PASS] Fault Prediction for LL (/predict-fault) -> HTTP 200, Predicted: LL, Probabilities calculated
  [PASS] Fault Prediction for LLG (/predict-fault) -> HTTP 200, Predicted: LLG, Probabilities calculated
  [PASS] Fault Prediction for LLL (/predict-fault) -> HTTP 200, Predicted: LLLG, Probabilities calculated
  [PASS] Fault Prediction for LLLG (/predict-fault) -> HTTP 200, Predicted: LLL, Probabilities calculated

5. Verifying RAG Maintenance Chatbot (/chat)...
  [PASS] Query: 'What are the safety precautions for circuit breaker maintenance?' -> HTTP 200, 1098 chars, 1 source cited
  [PASS] Query: 'How often should power transformer oil undergo DGA testing?' -> HTTP 200, 1131 chars, 1 source cited
  [PASS] Query: 'What causes Buchholz relay trips in power transformers?' -> HTTP 200, 1764 chars, 1 source cited

======================================================================
ALL TESTS PASSED SUCCESSFULLY! ZERO DEFECTS DETECTED.
======================================================================
```

---

## 8. Identified Architectural Gaps & Transition Risks for VoltSage AI

Before proceeding to subsequent stages, the following architectural gaps and transition requirements are documented:

1. **Authentication Absence:** Currently, there is zero authentication. All endpoints are open and unauthenticated. In Stage 3, a clean, local demonstration SQLite authentication layer (`users` table, password hashing via `passlib[bcrypt]` or `hashlib/hmac`, `HttpOnly` session cookies) must be introduced without breaking existing routes or ML prediction APIs.
2. **CORS & Credentials:** The current CORS middleware uses `allow_origins=["*"]` with `allow_credentials=False`. For cookie authentication to function properly in modern browsers, `allow_origins` must specify explicit origins (e.g., `["http://127.0.0.1:8000", "http://localhost:8000"]`) when `allow_credentials=True`.
3. **Chat History Persistence:** Currently, conversations are only held in client-side memory and reset on full refresh. In Stage 4, a server-side SQLite schema (`conversations` and `messages` tables) linked to the authenticated `user_id` must be created.
4. **Rate Limits & API Resilience:** On Gemini free-tier accounts, bursts of questions can encounter HTTP 429. The current fallback provides raw technical manual snippets. This boundary must remain intact throughout all stages.
5. **Branding Transition:** The visible branding will transition to **VoltSage AI**, retaining `PRJ_232` as the B.Tech project code in headers, footers, and metadata.

---

## 9. Checkpoint & Rollback Details

- **Git Branch:** `feature/voltsage-ai-upgrade`
- **Git Commit Hash:** `33f2e6f`
- **Git Tag:** `stage1-checkpoint`
- **Rollback Command:**
  ```powershell
  git checkout stage1-checkpoint
  ```
- **Local Startup Verification:**
  ```powershell
  .\run_project.bat
  ```
  Verified to locate `.venv\Scripts\python.exe`, launch the browser at `http://127.0.0.1:8000`, and start Uvicorn synchronously.
