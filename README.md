# VoltSage AI (PRJ_232) — Substation Electrical Intelligence

**Academic Context:** Final-Year B.Tech Major Project (PRJ_232)  
**Branch:** `feature/voltsage-ai-upgrade`  
**Checkpoint Tag:** `stage2-checkpoint`  
**Status:** Local Implementation & Verification Complete (**100% PASS RATE**)  
**Deployment State:** Verified Locally — HELD FOR USER REVIEW (DO NOT DEPLOY PUBLICLY)

---

## 1. Project Overview

**VoltSage AI** is an industrial-grade SCADA decision-support platform designed for electrical transmission and distribution substations. The platform seamlessly integrates:

1. **3-Phase Symmetrical & Asymmetrical Fault Classification:**
   - Powered by a trained **Random Forest** ensemble model (`ml/artifacts/best_fault_model.joblib`) with 100 decision trees.
   - Evaluates real physical inputs: 3-phase currents ($I_a, I_b, I_c$) and voltages ($V_a, V_b, V_c$).
   - Predicts 6 physical transmission states: `Normal`, `LG` (Line-to-Ground), `LL` (Line-to-Line), `LLG` (Double Line-to-Ground), `LLL` (Three-Phase Symmetrical), and `LLLG` (Three-Phase-to-Ground).
   - Achieves **86.9% validation accuracy** and **85.3% test split accuracy** with zero synthetic approximations.

2. **Technical Maintenance Copilot (RAG & Real-Time Streaming):**
   - **Interactive Technical Assistant:** Answers complex substation engineering queries (e.g., transformer oil dielectric breakdown testing, circuit breaker contact wear thresholds, protection relay trip diagnostics, and safety lockout/tagout procedures).
   - **Real-Time Streaming Generation:** Employs Server-Sent Events (SSE) via `/chat/stream` powered by **Google Gemini** (`gemini-3.5-flash`), delivering progressive token output with an active thinking status indicator.
   - **Grounded Engineering Citations:** RAG retrieval over **885 indexed technical document chunks** extracted from manufacturer manuals and standards:
     - **ABB MV/LV Technical Guide:** Medium-voltage switchgear, substation civil layout, and earthing grid design.
     - **Schneider Electric Masterpact NT/NW Guide:** Circuit breaker maintenance, field testing, and cluster lubrication.
     - **ETC Transformer Manual:** Oil-immersed distribution transformers, DGPT2/Buchholz protection, and oil sampling.
   - **Verified Metadata:** Cites exact document titles and verified page numbers with an automatic fallback mechanism for unsupported questions.

3. **Secure Authentication & Strict User Data Isolation:**
   - Split-screen authentication portal with **PBKDF2-HMAC-SHA256** password hashing (260,000 iterations, 16-byte random salt).
   - `HttpOnly` cookie session management with bearer token support.
   - Server-side route protection: unauthenticated requests to `/` or protected pages automatically redirect to `/login`.
   - SQLite relational storage (`data/voltsage.db`) with `PRAGMA foreign_keys = ON;`, cascade deletion, and multi-user data isolation.

4. **Industrial SCADA Chat Workspace:**
   - Dark industrial aesthetic with cyan (`#00d2ff`) and electric-blue accents.
   - Prominent **orange New Chat button** (`#ff6b35` to `#f97316`).
   - Conversation history categorized into **Today**, **Yesterday**, and **Earlier**.
   - User profile card in sidebar with role label **User** (replacing Operator) and working logout.
   - Multi-line textarea (`Shift+Enter` for newline, `Enter` to send), clipboard copy response, and quick prompt pills.

---

## 2. Local Setup & Execution Instructions

### Prerequisites
- **Python 3.10+ / Python 3.11** installed on your system.
- **Google Gemini API Key** (required for generative maintenance chatbot reasoning).

### Step 1: Environment Variables Configuration
Create a `.env` file in the project root directory with your Gemini API key and model selection:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
```

### Step 2: Virtual Environment & Dependencies
Create and activate an isolated Python virtual environment, then install dependencies:
```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```
```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Run the Application

#### Option A: Automated Windows Launcher (`run_project.bat`)
Double-click `run_project.bat` from Windows File Explorer or run in terminal:
```cmd
.\run_project.bat
```
The script validates your `.venv`, opens your browser to `http://127.0.0.1:8000`, and starts the Uvicorn server.

#### Option B: Direct Command Line
```powershell
& .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000` in Google Chrome or any modern browser.

---

## 3. Pre-Seeded Demonstration Accounts

For presentation and evaluation, pre-seeded accounts are active in `data/voltsage.db`:

| Account | Email | Password | Role |
|---|---|---|---|
| **Lead Substation Engineer** | `engineer@voltsage.internal` | `VoltSage#2026` | User |
| **Field Technician** | `operator.raj@voltsage.internal` | `Substation#2026` | User |
| **Relay Specialist** | `engineer.priya@voltsage.internal` | `Protection#2026` | User |

*New engineering accounts can also be registered directly on the split-screen sign-in portal.*

---

## 4. Automated Test Verification

A dedicated end-to-end regression and security test suite (`test_voltsage_upgrade.py`) verifies all routes, authentication, user isolation, ML classification, and RAG retrieval:

```powershell
& .\.venv\Scripts\python.exe test_voltsage_upgrade.py
```

### Verification Results Summary:
- **Suite 1: Gatekeeping, Redirects & Split-Screen Login:**
  - `GET /` (logged-out) -> HTTP 302 Redirect to `/login` [PASS]
  - `GET /` (followed) -> HTTP 200 at `/login` [PASS]
  - `GET /maintenance.html` (logged-out) -> HTTP 302 Redirect to `/login` [PASS]
  - `GET /index.html` (logged-out) -> HTTP 302 Redirect to `/login` [PASS]
  - `GET /fault-analysis.html` (logged-out) -> HTTP 302 Redirect to `/login` [PASS]
  - `GET /knowledge-base.html` (logged-out) -> HTTP 302 Redirect to `/login` [PASS]
  - `GET /checklists.html` (logged-out) -> HTTP 302 Redirect to `/login` [PASS]
  - `GET /settings.html` (logged-out) -> HTTP 302 Redirect to `/login` [PASS]
  - `GET /about.html` (logged-out) -> HTTP 302 Redirect to `/login` [PASS]
  - `POST /chat` (logged-out) -> HTTP 401 Unauthorized [PASS]
- **Suite 2: Authentication, Sessions & User Isolation:**
  - Password $\ge 6$ chars validation [PASS]
  - User registration & duplicate rejection [PASS]
  - Invalid password rejection [PASS]
  - Valid login & `HttpOnly` session cookie [PASS]
  - `GET /` (authenticated) -> HTTP 302 Redirect to `/maintenance.html` [PASS]
  - `GET /maintenance.html` (authenticated) -> HTTP 200 OK [PASS]
  - Conversation creation, chat persistence, renaming [PASS]
  - User B cross-account access blocked (HTTP 404 on User A conversations) [PASS]
  - Conversation deletion & cascade [PASS]
  - Session invalidation on logout [PASS]
- **Suite 3: 3-Phase Fault Classifier (Random Forest 6-Class):**
  - Normal, LG, LL, LLG, LLL, LLLG predictions verified [PASS]
- **Suite 4: Database Security & Cipher Verification:**
  - SQLite tables `users`, `sessions`, `conversations`, `messages` verified [PASS]
  - Zero plaintext passwords; all hashes verified PBKDF2-HMAC-SHA256 [PASS]

**Overall Result: 100% PASS RATE (28 / 28 Automated Assertions)**

---

## 5. Modified & Added Files

- `backend/database.py`: SQLite initialization, PBKDF2 password hashing, session tokens, user-isolated conversation and message storage.
- `backend/main.py`: Route protection, login redirects, `/api/auth/*` endpoints, `/api/conversations/*` endpoints, authenticated `/chat` persistence.
- `frontend/login.html`: Split-screen authentication page inspired by reference design with genuine technical feature highlights and password visibility toggle.
- `frontend/register.html`: Unified redirect to split-screen register view.
- `frontend/maintenance.html`: Upgraded AI chat workspace with prominent orange New Chat button, sidebar navigation, conversation list, and "Let's solve substation maintenance challenges" welcome cards.
- `frontend/js/maintenance.js`: Conversation date grouping (Today, Yesterday, Earlier), dynamic search, inline rename/delete, message formatting, and copy response.
- `frontend/js/auth.js`: Client-side route guard, navbar user state, and sidebar user profile management.
- `frontend/css/industrial.css`: SCADA industrial theme tokens, split-screen auth styles, orange New Chat button, and conversation item styles.
- `test_voltsage_upgrade.py`: Comprehensive automated regression and security test runner.
- `run_project.bat`: One-click Windows project launcher.
- `TEST_REPORT.md`: Comprehensive test execution log and technical verification report.

---

## 6. Known Limitations & Architecture Notes

1. **Email Service Delivery:**
   - In accordance with the local demonstration scope, email verification links and password reset emails are not connected to an external cloud SMTP provider (e.g. AWS SES or SendGrid). Accounts are activated immediately upon registration.
2. **Database Engine:**
   - SQLite is utilized for local evaluation, portability, and zero-configuration demonstration. For a distributed cloud deployment, the data access layer in `backend/database.py` would connect to PostgreSQL or Google Cloud SQL.

---

## 7. Rollback Instructions

If it is ever necessary to revert to the pre-upgrade state:
```powershell
# To revert to the start of this stage:
git checkout stage2-checkpoint

# To revert to the initial project baseline:
git checkout stage1-checkpoint
```

---

## 8. Deployment Recommendation

- **Local Evaluation & Demonstration:** **READY.** The application is fully functional, tested, and verifiable via `run_project.bat`.
- **Public Cloud Deployment:** **HELD.** Per project guidelines, public deployment is paused for user review and approval.
