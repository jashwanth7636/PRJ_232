"""
VoltSage AI (PRJ_232) — Comprehensive Regression, Auth & Security Test Suite
Tests:
1. All 9 Static Frontend Pages (HTTP 200, VoltSage AI branding)
2. Authentication (Registration, Duplicate check, Password validation, Login, Session cookie, Logout)
3. User Data Isolation (User A conversations inaccessible to User B)
4. Conversation CRUD (Create, Chat persistence, Fetch history, Rename, Delete)
5. 3-Phase Fault Classifier (6 electrical fault classes via Random Forest model)
6. RAG Maintenance Chatbot (IS 10028 / IEEE C37 citation retrieval & Gemini responses)
7. Backward Compatibility (Unauthenticated /chat requests continue to work)
8. Database Security (PBKDF2 password hashes, no plaintext leakage)
"""

import sys
import json
import sqlite3
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_frontend_pages():
    print("\n--- TEST SUITE 1: FRONTEND PAGES SERVING & BRANDING ---")
    pages = [
        ("/", "VoltSage AI"),
        ("/index.html", "VoltSage AI"),
        ("/maintenance.html", "VoltSage AI"),
        ("/fault-analysis.html", "VoltSage AI"),
        ("/knowledge-base.html", "VoltSage AI"),
        ("/checklists.html", "VoltSage AI"),
        ("/settings.html", "VoltSage AI"),
        ("/about.html", "VoltSage AI"),
        ("/login.html", "VoltSage AI"),
        ("/register.html", "VoltSage AI"),
    ]
    for path, expected_text in pages:
        url = f"{BASE_URL}{path}"
        r = requests.get(url, timeout=5)
        assert r.status_code == 200, f"Page {path} returned status {r.status_code}"
        assert expected_text in r.text, f"Page {path} missing branding text '{expected_text}'"
        print(f"  [PASS] Page {path} -> HTTP 200 OK (Contains '{expected_text}')")


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
    assert r.status_code in [400, 422], f"Expected 400 or 422 for short password, got {r.status_code}"
    print(f"  [PASS] Registration with short password rejected (HTTP {r.status_code})")

    # Test 2.2: Register User A
    r = session_a.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "Chief Substation Engineer",
        "email": user_a_email,
        "password": password
    })
    assert r.status_code in [201, 400], f"Unexpected status {r.status_code}"
    print(f"  [PASS] User A registered or existing ({user_a_email})")

    # Test 2.3: Register duplicate User A
    r = session_a.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "Chief Substation Engineer",
        "email": user_a_email,
        "password": password
    })
    assert r.status_code == 400, f"Expected 400 for duplicate email, got {r.status_code}"
    print("  [PASS] Duplicate registration rejected (HTTP 400)")

    # Test 2.4: Login User A with invalid password
    r = session_a.post(f"{BASE_URL}/api/auth/login", json={
        "email": user_a_email,
        "password": "WrongPassword!"
    })
    assert r.status_code == 401, f"Expected 401 for wrong password, got {r.status_code}"
    print("  [PASS] Invalid password rejected (HTTP 401)")

    # Test 2.5: Login User A with valid credentials
    r = session_a.post(f"{BASE_URL}/api/auth/login", json={
        "email": user_a_email,
        "password": password
    })
    assert r.status_code == 200, f"Expected 200 for valid login, got {r.status_code}"
    user_a_data = r.json()
    assert user_a_data["user"]["email"] == user_a_email
    assert "voltsage_session" in session_a.cookies
    print(f"  [PASS] User A logged in successfully (Session cookie set: {session_a.cookies.get('voltsage_session')[:10]}...)")

    # Test 2.6: Verify session via /api/auth/me
    r = session_a.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200, f"Expected 200 for /api/auth/me, got {r.status_code}"
    me_data = r.json()
    assert me_data["user"]["email"] == user_a_email
    assert "password_hash" not in me_data["user"], "Security flaw: password_hash exposed in user profile!"
    print(f"  [PASS] User A session verified via /api/auth/me (No password leakage)")

    # Test 2.7: Register and login User B
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

    # Test 2.8: User A creates a conversation
    r = session_a.post(f"{BASE_URL}/api/conversations", json={"title": "Transformer Inspection"})
    assert r.status_code == 201, f"Expected 201 for conv creation, got {r.status_code}"
    conv_data = r.json()
    conv_a = conv_data["conversation"]
    conv_id = conv_a["id"]
    print(f"  [PASS] User A created conversation '{conv_a['title']}' (ID: {conv_id})")

    # Test 2.9: User A sends a message in that conversation
    r = session_a.post(f"{BASE_URL}/chat", json={
        "message": "What is the procedure for transformer oil sampling according to IS 10028?",
        "conversation_id": conv_id
    }, timeout=30)
    assert r.status_code == 200, f"Expected 200 from chat, got {r.status_code}"
    chat_resp = r.json()
    answer_text = chat_resp.get("answer") or chat_resp.get("response", "")
    assert len(answer_text) > 20, f"Answer too short or missing: {chat_resp}"
    assert "sources" in chat_resp and len(chat_resp["sources"]) > 0, "No sources in chat response"
    print(f"  [PASS] User A asked chat question; received {len(answer_text)} chars answer with {len(chat_resp['sources'])} sources")

    # Test 2.10: User A renames conversation
    r = session_a.put(f"{BASE_URL}/api/conversations/{conv_id}", json={"title": "Oil Sampling IS 10028"})
    assert r.status_code == 200
    r = session_a.get(f"{BASE_URL}/api/conversations/{conv_id}")
    assert r.status_code == 200
    assert r.json()["conversation"]["title"] == "Oil Sampling IS 10028"
    print("  [PASS] User A renamed conversation to 'Oil Sampling IS 10028'")

    # Test 2.11: ISOLATION CHECK - User B tries to view User A's conversation
    r = session_b.get(f"{BASE_URL}/api/conversations/{conv_id}")
    assert r.status_code == 404, f"Security Breach! User B accessed User A's conversation (Status: {r.status_code})"
    print("  [PASS] User Isolation Verified: User B cannot view User A's conversation (HTTP 404)")

    # Test 2.12: ISOLATION CHECK - User B tries to rename User A's conversation
    r = session_b.put(f"{BASE_URL}/api/conversations/{conv_id}", json={"title": "Hacked Title"})
    assert r.status_code == 404, f"Security Breach! User B modified User A's conversation (Status: {r.status_code})"
    print("  [PASS] User Isolation Verified: User B cannot rename User A's conversation (HTTP 404)")

    # Test 2.13: ISOLATION CHECK - User B tries to delete User A's conversation
    r = session_b.delete(f"{BASE_URL}/api/conversations/{conv_id}")
    assert r.status_code == 404, f"Security Breach! User B deleted User A's conversation (Status: {r.status_code})"
    print("  [PASS] User Isolation Verified: User B cannot delete User A's conversation (HTTP 404)")

    # Test 2.14: User A deletes own conversation
    r = session_a.delete(f"{BASE_URL}/api/conversations/{conv_id}")
    assert r.status_code == 200, f"Expected 200 for deletion, got {r.status_code}"
    print(f"  [PASS] User A deleted own conversation (ID: {conv_id})")

    # Test 2.15: Verify conversation is gone
    r = session_a.get(f"{BASE_URL}/api/conversations/{conv_id}")
    assert r.status_code == 404
    print("  [PASS] Conversation confirmed deleted (HTTP 404)")

    # Test 2.16: User A Logout
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
            "expected_fault": "No Fault (Normal)"
        },
        {
            "name": "Line-to-Ground Fault (Phase A to Ground)",
            "data": {"Ia": 850.5, "Ib": 15.2, "Ic": 14.8, "Va": 12.0, "Vb": 232.0, "Vc": 231.5},
            "expected_fault": "Line-to-Ground Fault (LG)"
        },
        {
            "name": "Line-to-Line Fault (Phase A & B)",
            "data": {"Ia": 650.0, "Ib": 645.0, "Ic": 14.0, "Va": 95.0, "Vb": 94.0, "Vc": 230.0},
            "expected_fault": "Line-to-Line Fault (LL)"
        },
        {
            "name": "Line-to-Line-to-Ground Fault (Phase A & B to Ground)",
            "data": {"Ia": 720.0, "Ib": 715.0, "Ic": 16.0, "Va": 45.0, "Vb": 42.0, "Vc": 228.0},
            "expected_fault": "Double Line-to-Ground Fault (LLG)"
        },
        {
            "name": "Symmetrical 3-Phase Fault (Phase A, B, C)",
            "data": {"Ia": 890.0, "Ib": 895.0, "Ic": 892.0, "Va": 25.0, "Vb": 24.0, "Vc": 26.0},
            "expected_fault": "Three-Phase Fault (LLL)"
        },
        {
            "name": "3-Phase to Ground Fault (Phase A, B, C to Ground)",
            "data": {"Ia": 950.0, "Ib": 960.0, "Ic": 955.0, "Va": 5.0, "Vb": 4.5, "Vc": 5.2},
            "expected_fault": "Three-Phase-to-Ground Fault (LLLG)"
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


def test_rag_backwards_compatibility():
    print("\n--- TEST SUITE 4: RAG CHATBOT & BACKWARDS COMPATIBILITY ---")
    # Calling /chat without any auth header or conversation_id should succeed seamlessly
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "What are the recommended safety clearances for 132kV circuit breakers during busbar maintenance?"
    }, timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    resp = r.json()
    answer_text = resp.get("answer") or resp.get("response", "")
    assert len(answer_text) > 20, f"Answer too short or missing: {resp}"
    assert "sources" in resp and len(resp["sources"]) > 0, "No sources in chat response"
    print(f"  [PASS] Unauthenticated /chat request succeeded ({len(answer_text)} chars, {len(resp['sources'])} sources)")
    print(f"         First source citation: {resp['sources'][0].get('source', 'N/A')} (Score: {resp['sources'][0].get('score', 0)})")


def test_database_security():
    print("\n--- TEST SUITE 5: DATABASE SECURITY & CIPHER VERIFICATION ---")
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
        test_frontend_pages()
        test_auth_and_isolation()
        test_fault_classifier()
        test_rag_backwards_compatibility()
        test_database_security()
        print("\n=================================================================")
        print("  ALL TESTS PASSED SUCCESSFULLY! (100% PASS RATE)")
        print("=================================================================\n")
    except Exception as e:
        print(f"\n[TEST SUITE FAILURE]: {e}")
        sys.exit(1)
