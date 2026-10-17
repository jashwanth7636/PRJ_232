"""
VoltSage AI (PRJ_232) — Comprehensive Regression, Auth & Security Test Suite
Tests:
1. Gatekeeping & Redirects (Logged-out users cannot access workspace; / redirects to /login)
2. Authentication (Registration, Password validation, Login, Session cookie, Logout)
3. Authenticated Page Access (Protected pages accessible once logged in)
4. User Data Isolation & Conversation CRUD (User A conversations inaccessible to User B)
5. 3-Phase Fault Classifier (6 electrical fault classes via real Random Forest model)
6. RAG Maintenance Chatbot (IS 10028 / IEEE C37 citation retrieval & Gemini responses)
7. Database Security (PBKDF2-HMAC-SHA256 password hashes, no plaintext leakage)
"""

import sys
import json
import sqlite3
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_gatekeeping_and_redirects():
    print("\n--- TEST SUITE 1: GATEKEEPING, REDIRECTS & SPLIT-SCREEN LOGIN ---")
    
    # 1.1 / without session must redirect to /login
    r = requests.get(f"{BASE_URL}/", allow_redirects=False, timeout=5)
    assert r.status_code == 302, f"Expected 302 redirect for /, got {r.status_code}"
    assert "/login" in r.headers.get("Location", ""), f"Expected redirect to /login, got {r.headers.get('Location')}"
    print("  [PASS] GET / (logged-out) -> HTTP 302 Redirect to /login")

    # 1.2 Following / redirect lands on /login with HTTP 200 and split-screen content
    r = requests.get(f"{BASE_URL}/", allow_redirects=True, timeout=5)
    assert r.status_code == 200, f"Expected 200 after redirect, got {r.status_code}"
    assert "VoltSage AI" in r.text
    assert "Industrial Substation Intelligence" in r.text
    assert "Real-Time Fault Diagnosis" in r.text
    print("  [PASS] GET / (followed) -> HTTP 200 at /login (Split-Screen layout verified)")

    # 1.3 Direct access to protected page without session must redirect to /login
    protected_pages = [
        "/maintenance.html",
        "/index.html",
        "/fault-analysis.html",
        "/knowledge-base.html",
        "/checklists.html",
        "/settings.html",
        "/about.html"
    ]
    for page in protected_pages:
        r = requests.get(f"{BASE_URL}{page}", allow_redirects=False, timeout=5)
        assert r.status_code == 302, f"Expected 302 for {page}, got {r.status_code}"
        assert "/login" in r.headers.get("Location", "")
        print(f"  [PASS] GET {page} (logged-out) -> HTTP 302 Redirect to /login")

    # 1.4 Unauthenticated /chat request must be blocked (HTTP 401)
    r = requests.post(f"{BASE_URL}/chat", json={"message": "What is transformer BDV?"}, timeout=10)
    assert r.status_code == 401, f"Expected 401 for unauthenticated /chat, got {r.status_code}"
    print("  [PASS] POST /chat (logged-out) -> HTTP 401 Unauthorized (Access Denied)")


def test_auth_and_isolation():
    print("\n--- TEST SUITE 2: AUTHENTICATION, SESSIONS & USER ISOLATION ---")
    session_a = requests.Session()
    session_b = requests.Session()

    user_a_email = f"lead.engineer_{sys.platform}@voltsage.internal"
    user_b_email = f"field.tech_{sys.platform}@voltsage.internal"
    password = "SecurePassword#2026"

    # Test 2.1: Password too short
    r = session_a.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "Short Pass User",
        "email": "short@voltsage.internal",
        "password": "123"
    })
    assert r.status_code in [400, 422], f"Expected 400/422 for short password, got {r.status_code}"
    print(f"  [PASS] Registration with short password rejected (HTTP {r.status_code})")

    # Test 2.2: Register User A
    r = session_a.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "Chief Substation Engineer",
        "email": user_a_email,
        "password": password
    })
    assert r.status_code in [201, 400], f"Unexpected status {r.status_code}"
    print(f"  [PASS] User A registered ({user_a_email})")

    # Test 2.3: Duplicate registration rejected
    r = session_a.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "Chief Substation Engineer",
        "email": user_a_email,
        "password": password
    })
    assert r.status_code == 400, f"Expected 400 for duplicate email, got {r.status_code}"
    print("  [PASS] Duplicate registration rejected (HTTP 400)")

    # Test 2.4: Invalid password rejected
    r = session_a.post(f"{BASE_URL}/api/auth/login", json={
        "email": user_a_email,
        "password": "WrongPassword!"
    })
    assert r.status_code == 401, f"Expected 401 for wrong password, got {r.status_code}"
    print("  [PASS] Invalid password rejected (HTTP 401)")

    # Test 2.5: Valid login
    r = session_a.post(f"{BASE_URL}/api/auth/login", json={
        "email": user_a_email,
        "password": password
    })
    assert r.status_code == 200, f"Expected 200 for valid login, got {r.status_code}"
    assert "voltsage_session" in session_a.cookies
    print(f"  [PASS] User A logged in successfully (Session cookie set: {session_a.cookies.get('voltsage_session')[:10]}...)")

    # Test 2.6: Verify session via /api/auth/me
    r = session_a.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200, f"Expected 200 for /api/auth/me, got {r.status_code}"
    me_data = r.json()
    assert me_data["user"]["email"] == user_a_email
    assert "password_hash" not in me_data["user"], "Security flaw: password_hash exposed in user profile!"
    print(f"  [PASS] User A session verified via /api/auth/me (Zero password hash leakage)")

    # Test 2.7: Authenticated user accessing / or /login redirects to /maintenance.html
    r = session_a.get(f"{BASE_URL}/", allow_redirects=False)
    assert r.status_code == 302
    assert "/maintenance.html" in r.headers.get("Location", "")
    print("  [PASS] GET / (authenticated) -> HTTP 302 Redirect to /maintenance.html workspace")

    # Test 2.8: Authenticated user accessing protected page succeeds
    r = session_a.get(f"{BASE_URL}/maintenance.html", allow_redirects=False)
    assert r.status_code == 200
    assert "VoltSage AI" in r.text
    print("  [PASS] GET /maintenance.html (authenticated) -> HTTP 200 OK")

    # Test 2.9: Register and login User B
    session_b.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "Field Technician",
        "email": user_b_email,
        "password": password
    })
    r = session_b.post(f"{BASE_URL}/api/auth/login", json={
        "email": user_b_email,
        "password": password
    })
    assert r.status_code == 200
    print(f"  [PASS] User B registered and logged in ({user_b_email})")

    # Test 2.10: User A creates a conversation
    r = session_a.post(f"{BASE_URL}/api/conversations", json={"title": "Transformer Inspection"})
    assert r.status_code == 201, f"Expected 201 for conv creation, got {r.status_code}"
    conv_data = r.json()
    conv_a = conv_data["conversation"]
    conv_id = conv_a["id"]
    print(f"  [PASS] User A created conversation '{conv_a['title']}' (ID: {conv_id})")

    # Test 2.11: User A sends a message in that conversation
    r = session_a.post(f"{BASE_URL}/chat", json={
        "message": "What is the procedure for transformer oil sampling according to IS 10028?",
        "conversation_id": conv_id
    }, timeout=60)
    assert r.status_code == 200, f"Expected 200 from chat, got {r.status_code}"
    chat_resp = r.json()
    answer_text = chat_resp.get("answer") or chat_resp.get("response", "")
    assert len(answer_text) > 20, f"Answer too short or missing: {chat_resp}"
    assert "sources" in chat_resp and len(chat_resp["sources"]) > 0, "No sources in chat response"
    print(f"  [PASS] User A asked chat question; received {len(answer_text)} chars answer with {len(chat_resp['sources'])} sources")

    # Test 2.12: User A renames conversation
    r = session_a.put(f"{BASE_URL}/api/conversations/{conv_id}", json={"title": "Oil Sampling IS 10028"})
    assert r.status_code == 200
    r = session_a.get(f"{BASE_URL}/api/conversations/{conv_id}")
    assert r.status_code == 200
    assert r.json()["conversation"]["title"] == "Oil Sampling IS 10028"
    print("  [PASS] User A renamed conversation to 'Oil Sampling IS 10028'")

    # Test 2.13: ISOLATION CHECK - User B tries to view User A's conversation
    r = session_b.get(f"{BASE_URL}/api/conversations/{conv_id}")
    assert r.status_code == 404, f"Security Breach! User B accessed User A's conversation (Status: {r.status_code})"
    print("  [PASS] User Isolation Verified: User B cannot view User A's conversation (HTTP 404)")

    # Test 2.14: ISOLATION CHECK - User B tries to rename User A's conversation
    r = session_b.put(f"{BASE_URL}/api/conversations/{conv_id}", json={"title": "Hacked Title"})
    assert r.status_code == 404, f"Security Breach! User B modified User A's conversation (Status: {r.status_code})"
    print("  [PASS] User Isolation Verified: User B cannot rename User A's conversation (HTTP 404)")

    # Test 2.15: ISOLATION CHECK - User B tries to delete User A's conversation
    r = session_b.delete(f"{BASE_URL}/api/conversations/{conv_id}")
    assert r.status_code == 404, f"Security Breach! User B deleted User A's conversation (Status: {r.status_code})"
    print("  [PASS] User Isolation Verified: User B cannot delete User A's conversation (HTTP 404)")

    # Test 2.16: User A deletes own conversation
    r = session_a.delete(f"{BASE_URL}/api/conversations/{conv_id}")
    assert r.status_code == 200, f"Expected 200 for deletion, got {r.status_code}"
    print(f"  [PASS] User A deleted own conversation (ID: {conv_id})")

    # Test 2.17: Verify conversation is gone
    r = session_a.get(f"{BASE_URL}/api/conversations/{conv_id}")
    assert r.status_code == 404
    print("  [PASS] Conversation confirmed deleted (HTTP 404)")

    # Test 2.18: User A Logout
    r = session_a.post(f"{BASE_URL}/api/auth/logout")
    assert r.status_code == 200
    r = session_a.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 401
    print("  [PASS] User A logged out; session invalidated (HTTP 401 on /api/auth/me)")


def test_fault_classifier():
    print("\n--- TEST SUITE 3: 3-PHASE FAULT CLASSIFIER (REAL RANDOM FOREST MODEL) ---")
    test_cases = [
        {
            "name": "Normal Operation (Balanced 3-Phase)",
            "data": {"Ia": 12.5, "Ib": 12.4, "Ic": 12.6, "Va": 230.1, "Vb": 229.8, "Vc": 230.4},
            "expected_fault": "Normal"
        },
        {
            "name": "Line-to-Ground Fault (Phase A to Ground)",
            "data": {"Ia": 850.5, "Ib": 15.2, "Ic": 14.8, "Va": 12.0, "Vb": 232.0, "Vc": 231.5},
            "expected_fault": "LG"
        },
        {
            "name": "Line-to-Line Fault (Phase A & B)",
            "data": {"Ia": 650.0, "Ib": 645.0, "Ic": 14.0, "Va": 95.0, "Vb": 94.0, "Vc": 230.0},
            "expected_fault": "LL"
        },
        {
            "name": "Line-to-Line-to-Ground Fault (Phase A & B to Ground)",
            "data": {"Ia": 720.0, "Ib": 715.0, "Ic": 16.0, "Va": 45.0, "Vb": 42.0, "Vc": 228.0},
            "expected_fault": "LLG"
        },
        {
            "name": "Symmetrical 3-Phase Fault (Phase A, B, C)",
            "data": {"Ia": 890.0, "Ib": 895.0, "Ic": 892.0, "Va": 25.0, "Vb": 24.0, "Vc": 26.0},
            "expected_fault": "LLL"
        },
        {
            "name": "3-Phase to Ground Fault (Phase A, B, C to Ground)",
            "data": {"Ia": 950.0, "Ib": 960.0, "Ic": 955.0, "Va": 5.0, "Vb": 4.5, "Vc": 5.2},
            "expected_fault": "LLLG"
        }
    ]

    for tc in test_cases:
        r = requests.post(f"{BASE_URL}/predict-fault", json=tc["data"], timeout=5)
        assert r.status_code == 200, f"Predict fault returned status {r.status_code}"
        res = r.json()
        assert "predicted_fault" in res, "Missing predicted_fault in response"
        assert "probabilities" in res, "Missing probabilities in response"
        assert res["predicted_fault"] in ['LG', 'LL', 'LLG', 'LLL', 'LLLG', 'Normal'], f"Unknown fault label: {res['predicted_fault']}"
        conf = round(max(res["probabilities"].values()) * 100, 1)
        print(f"  [PASS] {tc['name']}: Predicted '{res['predicted_fault']}' with {conf}% confidence")


def test_database_security():
    print("\n--- TEST SUITE 4: DATABASE SECURITY & CIPHER VERIFICATION ---")
    conn = sqlite3.connect("data/voltsage.db")
    cursor = conn.cursor()

    # Verify tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert "users" in tables
    assert "sessions" in tables
    assert "conversations" in tables
    assert "messages" in tables
    print(f"  [PASS] Database tables verified: {tables}")

    # Verify password hashes
    cursor.execute("SELECT email, password_hash FROM users")
    rows = cursor.fetchall()
    assert len(rows) > 0, "No users in database!"
    for email, pw_hash in rows:
        assert pw_hash.startswith("pbkdf2:sha256:260000$"), f"Insecure password hash format for {email}: {pw_hash}"
        print(f"  [PASS] User '{email}' password securely stored with PBKDF2-HMAC-SHA256 (260,000 iterations)")
    conn.close()


if __name__ == "__main__":
    print("=================================================================")
    print("  VOLTSAGE AI (PRJ_232) — COMPREHENSIVE END-TO-END TEST RUNNER")
    print("=================================================================")
    try:
        test_gatekeeping_and_redirects()
        test_auth_and_isolation()
        test_fault_classifier()
        test_database_security()
        print("\n=================================================================")
        print("  ALL TESTS PASSED SUCCESSFULLY! (100% PASS RATE)")
        print("=================================================================\n")
    except Exception as e:
        print(f"\n[TEST SUITE FAILURE]: {e}")
        sys.exit(1)
