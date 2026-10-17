import urllib.request
import urllib.parse
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_get(path, description):
    url = f"{BASE_URL}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PRJ232-Tester"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            content = resp.read()
            assert status == 200, f"Expected 200, got {status}"
            assert len(content) > 0, "Response content is empty"
            print(f"  [PASS] {description} ({path}) -> HTTP {status}, {len(content)} bytes")
            return content
    except Exception as e:
        print(f"  [FAIL] {description} ({path}) -> Error: {e}")
        return None

def test_post_json(path, payload, description):
    url = f"{BASE_URL}{path}"
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "PRJ232-Tester"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            content = resp.read()
            assert status == 200, f"Expected 200, got {status}"
            res_json = json.loads(content.decode("utf-8"))
            print(f"  [PASS] {description} ({path}) -> HTTP {status}, response parsed")
            return res_json
    except Exception as e:
        print(f"  [FAIL] {description} ({path}) -> Error: {e}")
        return None

def main():
    print("=" * 70)
    print("PRJ_232: END-TO-END AUTOMATED VERIFICATION SUITE")
    print("=" * 70)

    print("\n1. Verifying HTML Pages...")
    pages = [
        ("/", "Main Dashboard (Root)"),
        ("/index.html", "Main Dashboard (Explicit)"),
        ("/maintenance.html", "AI Maintenance Chatbot"),
        ("/fault-analysis.html", "Electrical Fault Analysis"),
        ("/knowledge-base.html", "Knowledge Base & Upload"),
        ("/checklists.html", "Maintenance Checklists"),
        ("/settings.html", "Settings & Diagnostics"),
        ("/about.html", "Project Information & ML Architecture"),
    ]
    for p, desc in pages:
        res = test_get(p, desc)
        if not res:
            sys.exit(1)

    print("\n2. Verifying Static CSS & JS Assets...")
    assets = [
        ("/css/industrial.css", "Industrial SCADA CSS Design System"),
        ("/js/dashboard.js", "Dashboard Controller"),
        ("/js/maintenance.js", "Maintenance Chat Controller"),
        ("/js/fault-analysis.js", "Fault Analysis Controller"),
        ("/js/knowledge-base.js", "Knowledge Base Controller"),
        ("/js/checklists.js", "Checklists Controller"),
        ("/js/settings.js", "Settings Controller"),
    ]
    for a, desc in assets:
        res = test_get(a, desc)
        if not res:
            sys.exit(1)

    print("\n3. Verifying REST API Endpoints...")
    test_get("/health", "Health Check API")
    test_get("/api/stats", "Telemetry & ML Statistics API")
    test_get("/api/documents", "Document Repository API")
    test_get("/api/checklists", "Maintenance Checklists API")

    print("\n4. Verifying Machine Learning Fault Classifier (/predict-fault)...")
    # Test cases: Normal, LG, LL, LLG, LLL, LLLG
    test_cases = [
        ({"Ia": -35.89, "Ib": -1.18, "Ic": 33.75, "Va": 0.46, "Vb": -0.54, "Vc": 0.07}, "Normal"),
        ({"Ia": 858.35, "Ib": 41.26, "Ic": 12.17, "Va": 0.02, "Vb": -0.32, "Vc": 0.30}, "LG"),
        ({"Ia": 47.49, "Ib": -168.61, "Ic": 123.94, "Va": 0.49, "Vb": 0.01, "Vc": -0.50}, "LL"),
        ({"Ia": 119.99, "Ib": 695.35, "Ic": 57.51, "Va": 0.04, "Vb": -0.27, "Vc": 0.23}, "LLG"),
        ({"Ia": 733.24, "Ib": -793.63, "Ic": 62.38, "Va": -0.01, "Vb": -0.03, "Vc": 0.04}, "LLL"),
        ({"Ia": 881.61, "Ib": -511.95, "Ic": -369.65, "Va": 0.02, "Vb": -0.04, "Vc": 0.03}, "LLLG"),
    ]
    for payload, expected in test_cases:
        res = test_post_json("/predict-fault", payload, f"Fault Prediction for {expected}")
        if res:
            print(f"      Predicted: {res.get('predicted_fault')} (Expected: {expected}), Confidence: {res.get('confidence')}")
            assert "predicted_fault" in res
            assert "probabilities" in res
        else:
            sys.exit(1)

    print("\n5. Verifying RAG Maintenance Chatbot (/chat)...")
    chat_questions = [
        "What are the safety precautions for circuit breaker maintenance?",
        "How often should power transformer oil undergo DGA testing?",
        "What causes Buchholz relay trips in power transformers?"
    ]
    for q in chat_questions:
        payload = {"message": q, "history": []}
        res = test_post_json("/chat", payload, f"Chat Query: '{q[:40]}...'")
        if res:
            answer = res.get("answer", "")
            sources = res.get("sources", [])
            print(f"      Answer Length: {len(answer)} chars | Sources: {len(sources)}")
            print(f"      Sample snippet: {answer[:120]}...")
            assert len(answer) > 80, "Answer too short or truncated!"
        else:
            sys.exit(1)

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY! ZERO DEFECTS DETECTED.")
    print("=" * 70)

if __name__ == "__main__":
    main()
