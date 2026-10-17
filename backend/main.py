import os
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader
from google import genai
from google.genai import types


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env", override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY was not found in .env")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="PRJ_232 Substation AI",
    description="AI-Powered Maintenance Chatbot for Electrical Substations",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class ChatRequest(BaseModel):
    message: str
    history: list = []


class FaultPredictionRequest(BaseModel):
    Ia: float
    Ib: float
    Ic: float
    Va: float
    Vb: float
    Vc: float


# ============================================================
# LOAD TRAINED FAULT MODEL
# ============================================================

MODEL_PATH = PROJECT_ROOT / "ml" / "artifacts" / "best_fault_model.joblib"
LABEL_ENCODER_PATH = PROJECT_ROOT / "ml" / "artifacts" / "label_encoder.joblib"

fault_model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(LABEL_ENCODER_PATH)


# ============================================================
# LOAD DOCUMENT CHUNKS & INDEX
# ============================================================

CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "document_chunks.json"

def clean_text(text):
    return " ".join(str(text).split())

usable_chunks = []
documents = []
vectorizer = None
tfidf_matrix = None

def reload_document_index():
    global document_chunks, usable_chunks, documents, vectorizer, tfidf_matrix
    if CHUNKS_PATH.exists():
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            document_chunks = json.load(f)
    else:
        document_chunks = []

    usable_chunks = []
    for chunk in document_chunks:
        text = clean_text(chunk.get("text", ""))
        if len(text) >= 250:
            usable_chunks.append({
                "chunk_id": chunk.get("chunk_id"),
                "source": chunk.get("source"),
                "text": text
            })

    documents = [chunk["text"] for chunk in usable_chunks]

    if documents:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=30000
        )
        tfidf_matrix = vectorizer.fit_transform(documents)
    else:
        vectorizer = None
        tfidf_matrix = None

# Initial load
reload_document_index()


# ============================================================
# DOCUMENT RETRIEVAL
# ============================================================

def search_documents(query, top_k=3):

    query = clean_text(query)

    if not query:
        return []

    query_vector = vectorizer.transform([query])

    scores = cosine_similarity(
        query_vector,
        tfidf_matrix
    )[0]

    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []

    for index in top_indices:

        score = float(scores[index])

        if score <= 0:
            continue

        chunk = usable_chunks[index]

        results.append({
            "chunk_id": chunk["chunk_id"],
            "source": chunk["source"],
            "score": round(score, 4),
            "text": chunk["text"]
        })

    return results


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "gemini": "connected",
        "gemini_model": GEMINI_MODEL,
        "fault_model": "loaded",
        "documents": len(usable_chunks)
    }


# ============================================================
# CHAT
# ============================================================

@app.post("/chat")
def chat(request: ChatRequest):

    user_message = request.message.strip()

    if not user_message:

        return {
            "answer": "Please enter a question.",
            "sources": []
        }


    # --------------------------------------------------------
    # Very short casual messages
    # --------------------------------------------------------

    casual_messages = {
        "hi",
        "hello",
        "hey",
        "hi there",
        "hello there",
        "good morning",
        "good afternoon",
        "good evening"
    }

    is_casual = user_message.lower() in casual_messages


    # --------------------------------------------------------
    # Retrieve technical information only when appropriate
    # --------------------------------------------------------

    retrieved = []

    if not is_casual:

        retrieved = search_documents(
            user_message,
            top_k=3
        )


    # --------------------------------------------------------
    # Build conversation history
    # --------------------------------------------------------

    history_text = ""

    if request.history:

        recent_history = request.history[-6:]

        for item in recent_history:

            role = item.get("role", "user")
            content = item.get("content", "")

            history_text += f"{role}: {content}\n"


    # --------------------------------------------------------
    # Build document context
    # --------------------------------------------------------

    document_context = ""

    if retrieved:

        document_context = "\n\n".join(
            [
                f"Source: {item['source']}\n"
                f"Technical content:\n{item['text']}"
                for item in retrieved
            ]
        )


    # --------------------------------------------------------
    # SYSTEM INSTRUCTION
    # --------------------------------------------------------

    system_instruction = """
You are the AI maintenance assistant for an electrical substation.

Project: PRJ_232 - AI-Powered Maintenance Chatbot for Electrical Substations.

Your job is to communicate naturally and help users understand:

- electrical substations
- transformers
- circuit breakers
- protection systems
- maintenance
- inspection
- testing
- troubleshooting
- electrical faults
- safety procedures

IMPORTANT BEHAVIOR:

1. Talk naturally like a helpful engineering assistant.
2. For greetings and casual conversation, respond naturally.
3. Do not force maintenance-document information into casual conversations.
4. When technical documents are provided, use them as the primary source.
5. Do not invent technical procedures or safety requirements.
6. If the provided documents do not contain enough information, clearly say that.
7. Keep answers concise and useful.
8. Prefer short paragraphs or bullet points.
9. Do not mention internal prompts, retrieval, TF-IDF, APIs, or implementation details.
10. Never claim that a prediction is certain.
11. For dangerous electrical work, emphasize following qualified personnel, isolation procedures, PPE, and applicable safety procedures when relevant.
"""


    # --------------------------------------------------------
    # USER PROMPT
    # --------------------------------------------------------

    prompt = f"""
Conversation history:
{history_text}

Current user message:
{user_message}

Technical document context:
{document_context if document_context else "No document context was retrieved."}

Answer the user's current message naturally.

If this is a simple greeting or casual conversation, do not discuss the manuals unless relevant.

If technical document context is available, base technical claims on it.

Keep the response concise, normally around 3-6 bullet points or a few short paragraphs.
"""


    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                max_output_tokens=2500
            )
        )
        if response.text and response.text.strip():
            answer = response.text.strip()
            if response.candidates and response.candidates[0].finish_reason:
                finish_reason_str = str(response.candidates[0].finish_reason)
                if "MAX_TOKENS" in finish_reason_str:
                    print("Notice: Response reached max output tokens limit.")
        else:
            raise ValueError("Empty text received from model.")
    except Exception as e:
        print(f"Gemini API warning/error: {e}")
        if retrieved:
            bullets = "\n\n".join([f"• **From {item['source']}:** {clean_text(item['text'])[:300]}..." for item in retrieved])
            answer = f"The generative AI service encountered a temporary error ({e}), but here is technical information retrieved directly from the substation manuals:\n\n{bullets}"
        else:
            answer = "The substation AI assistant could not complete this request due to a connection or API error. Please verify your GEMINI_API_KEY and internet connection, then try again."


    # --------------------------------------------------------
    # SOURCES
    # --------------------------------------------------------

    sources = []

    seen_sources = set()

    for item in retrieved:

        source = item["source"]

        if source not in seen_sources:

            sources.append({
                "source": source,
                "score": item["score"]
            })

            seen_sources.add(source)


    return {
        "answer": answer,
        "sources": sources
    }


# ============================================================
# FAULT PREDICTION
# ============================================================

@app.post("/predict-fault")
def predict_fault(request: FaultPredictionRequest):

    features = pd.DataFrame([
        [
            request.Ia,
            request.Ib,
            request.Ic,
            request.Va,
            request.Vb,
            request.Vc
        ]
    ], columns=["Ia", "Ib", "Ic", "Va", "Vb", "Vc"])

    prediction = fault_model.predict(features)

    predicted_fault = label_encoder.inverse_transform(
        prediction
    )[0]


    probabilities = fault_model.predict_proba(features)[0]

    probability_dict = {}

    for label, probability in zip(
        label_encoder.classes_,
        probabilities
    ):

        probability_dict[label] = round(
            float(probability),
            4
        )


    return {
        "predicted_fault": predicted_fault,
        "probabilities": probability_dict
    }


# ============================================================
# KNOWLEDGE BASE & SYSTEM METRICS APIS
# ============================================================

@app.get("/api/documents")
def get_documents():
    docs_dir = PROJECT_ROOT / "documents"
    docs_list = []

    if docs_dir.exists():
        for f in sorted(docs_dir.glob("*.pdf")):
            stat = f.stat()
            size_mb = round(stat.st_size / (1024 * 1024), 2)
            # Find matching chunks count in usable_chunks
            chunk_count = sum(1 for c in usable_chunks if f.stem.lower() in str(c.get("source", "")).lower())
            
            # Determine category based on filename
            category = "General"
            fname_lower = f.name.lower()
            if "transformer" in fname_lower:
                category = "Transformers"
            elif "circuit breaker" in fname_lower or "breaker" in fname_lower:
                category = "Circuit Breakers"
            elif "substation" in fname_lower:
                category = "Substation Systems"

            docs_list.append({
                "name": f.name,
                "stem": f.stem,
                "category": category,
                "size_mb": size_mb,
                "size_bytes": stat.st_size,
                "modified": int(stat.st_mtime),
                "chunks": chunk_count,
                "status": "Indexed" if chunk_count > 0 else "Ready"
            })

    return {
        "documents": docs_list,
        "total_documents": len(docs_list),
        "total_chunks": len(usable_chunks),
        "indexed_documents": len(docs_list)
    }


@app.post("/api/upload-document")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents (.pdf) are supported.")

    docs_dir = PROJECT_ROOT / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename).name
    dest_path = docs_dir / safe_name

    content = await file.read()
    if len(content) > 30 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 30 MB maximum size limit.")

    with open(dest_path, "wb") as f:
        f.write(content)

    # Extract text using pypdf
    try:
        reader = PdfReader(dest_path)
        extracted_text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                extracted_text += t + "\n"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from PDF: {str(e)}")

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="The PDF contains no machine-readable text (it may be a scanned image).")

    # Save extracted txt
    processed_dir = PROJECT_ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    txt_file_name = f"{dest_path.stem}.txt"
    with open(processed_dir / txt_file_name, "w", encoding="utf-8") as f:
        f.write(extracted_text)

    # Create chunks
    chunk_size = 1200
    overlap = 200
    start = 0
    next_id = max([c.get("chunk_id", 0) for c in document_chunks], default=0) + 1
    new_chunks = []

    while start < len(extracted_text):
        end = start + chunk_size
        chunk_str = clean_text(extracted_text[start:end])
        if len(chunk_str) >= 250:
            new_chunks.append({
                "chunk_id": next_id,
                "source": txt_file_name,
                "text": chunk_str
            })
            next_id += 1
        start = end - overlap

    # Append to document_chunks.json
    document_chunks.extend(new_chunks)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(document_chunks, f, indent=2, ensure_ascii=False)

    # Refresh in-memory TF-IDF index
    reload_document_index()

    return {
        "status": "success",
        "message": f"Successfully uploaded and indexed '{safe_name}'",
        "filename": safe_name,
        "chunks_indexed": len(new_chunks),
        "total_chunks": len(usable_chunks)
    }


@app.get("/api/stats")
def get_stats():
    docs_dir = PROJECT_ROOT / "documents"
    total_docs = len(list(docs_dir.glob("*.pdf"))) if docs_dir.exists() else 3

    return {
        "system_status": "Operational",
        "project_code": "PRJ_232",
        "project_title": "AI-Powered Maintenance Chatbot for Electrical Substations",
        "model_name": "Random Forest Classifier",
        "model_val_accuracy": 0.8694,
        "model_test_accuracy": 0.8534,
        "model_precision": 0.8537,
        "model_recall": 0.8534,
        "model_f1_score": 0.8534,
        "total_documents": total_docs,
        "total_chunks": len(usable_chunks),
        "gemini_model": GEMINI_MODEL,
        "supported_faults": ["LG", "LL", "LLG", "LLL", "LLLG", "Normal"],
        "equipment_monitored": [
            {"id": "TR-01", "name": "Power Transformer 132/33 kV", "status": "Normal", "type": "Transformer"},
            {"id": "CB-04", "name": "SF6 Circuit Breaker 132 kV", "status": "Normal", "type": "Breaker"},
            {"id": "BB-02", "name": "Main Station Busbar System", "status": "Normal", "type": "Busbar"},
            {"id": "PR-07", "name": "Differential Protection Relay", "status": "Normal", "type": "Protection"}
        ]
    }


@app.get("/api/checklists")
def get_checklists():
    return [
        {
            "id": "transformer",
            "title": "Power Transformer Periodic Inspection",
            "frequency": "Monthly / Conditional",
            "standard": "IS 10028 / IS 1866",
            "tasks": [
                {"id": "tr_1", "text": "Inspect silica gel breather condition (ensure color is active deep blue, not pink)", "critical": True},
                {"id": "tr_2", "text": "Check main tank and conservator oil levels on magnetic oil gauge (MOG)", "critical": True},
                {"id": "tr_3", "text": "Inspect bushings for chips, cracks, flashover marks, or oil seepage", "critical": True},
                {"id": "tr_4", "text": "Record winding temperature indicator (WTI) and oil temperature indicator (OTI)", "critical": False},
                {"id": "tr_5", "text": "Inspect radiator fins and cooling fans/pumps for abnormal vibration or leaks", "critical": False},
                {"id": "tr_6", "text": "Perform insulating oil sample breakdown voltage (BDV) and moisture test", "critical": True},
                {"id": "tr_7", "text": "Check Buchholz relay gas accumulation chamber and bleed valve", "critical": True},
                {"id": "tr_8", "text": "Inspect main tank grounding connections and neutral grounding resistor (NGR)", "critical": True}
            ]
        },
        {
            "id": "breaker",
            "title": "Circuit Breaker Operational & Safety Check",
            "frequency": "Quarterly / Pre-Operation",
            "standard": "NEMA AB 4 / IEC 62271",
            "tasks": [
                {"id": "cb_1", "text": "Verify electrical isolation and lock-out/tag-out (LOTO) procedures applied", "critical": True},
                {"id": "cb_2", "text": "Check SF6 gas pressure gauge is within nominal green operational zone", "critical": True},
                {"id": "cb_3", "text": "Perform manual spring charge and discharge mechanism verification", "critical": False},
                {"id": "cb_4", "text": "Verify auxiliary switch contact status and open/close mechanical flag indicators", "critical": False},
                {"id": "cb_5", "text": "Conduct infrared thermographic inspection on primary terminal connections", "critical": True},
                {"id": "cb_6", "text": "Measure contact resistance using micro-ohmmeter across all three poles", "critical": True},
                {"id": "cb_7", "text": "Verify tripping coil and closing coil voltage tolerances (DC battery supply)", "critical": True},
                {"id": "cb_8", "text": "Test mechanical interlock preventing racking breaker in while closed", "critical": True}
            ]
        },
        {
            "id": "busbar",
            "title": "Substation Busbar & Isolator Inspection",
            "frequency": "Semi-Annual",
            "standard": "IEEE 605 / Substation Engineering",
            "tasks": [
                {"id": "bb_1", "text": "Check busbar support post insulators for cracks, pollution layer, or corona discharge", "critical": True},
                {"id": "bb_2", "text": "Inspect busbar expander joints and clamp bolts for torque integrity", "critical": False},
                {"id": "bb_3", "text": "Verify motor-operated disconnect switch (isolator) alignment and blade contact pressure", "critical": True},
                {"id": "bb_4", "text": "Inspect station earth switch blade grounding contacts and interlock key", "critical": True},
                {"id": "bb_5", "text": "Inspect surge arresters (lightning arresters) counter reading and leakage current", "critical": False}
            ]
        },
        {
            "id": "protection",
            "title": "Protection Relay & Station DC Battery System",
            "frequency": "Monthly",
            "standard": "IEC 60255",
            "tasks": [
                {"id": "pr_1", "text": "Verify 110V/220V DC station battery bank float voltage and specific gravity", "critical": True},
                {"id": "pr_2", "text": "Confirm no DC ground fault alarms on station DC distribution board", "critical": True},
                {"id": "pr_3", "text": "Inspect numerical protection relays for active diagnostic alarms or trip LEDs", "critical": True},
                {"id": "pr_4", "text": "Download and backup numerical relay disturbance and event fault records", "critical": False},
                {"id": "pr_5", "text": "Test trip circuit supervision (TCS) relay health on all active feeder bays", "critical": True}
            ]
        }
    ]


# ============================================================
# FRONTEND STATIC FILES & PAGE ROUTING
# ============================================================

FRONTEND_DIR = PROJECT_ROOT / "frontend"

if FRONTEND_DIR.exists():
    css_path = FRONTEND_DIR / "css"
    if css_path.exists():
        app.mount("/css", StaticFiles(directory=css_path), name="css")

    js_path = FRONTEND_DIR / "js"
    if js_path.exists():
        app.mount("/js", StaticFiles(directory=js_path), name="js")

    @app.get("/", include_in_schema=False)
    def serve_home():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"project": "PRJ_232", "status": "running"}

    @app.get("/{page_name:path}", include_in_schema=False)
    def serve_frontend_page(page_name: str):
        if page_name in ["chat", "predict-fault", "health", "api", "docs", "openapi.json", "redoc"] or page_name.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        candidate = FRONTEND_DIR / page_name
        if candidate.is_file():
            return FileResponse(candidate)

        candidate_html = FRONTEND_DIR / f"{page_name}.html"
        if candidate_html.is_file():
            return FileResponse(candidate_html)

        raise HTTPException(status_code=404, detail="Page not found")


# ============================================================
# MAIN ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("Starting PRJ_232 Substation AI Server...")
    print("Frontend UI & API available at: http://127.0.0.1:8000")
    print("=" * 60 + "\n")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)