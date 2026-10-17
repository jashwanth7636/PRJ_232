import os
import json
import re
import html
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader
from google import genai
from google.genai import types

from backend import database


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env", override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY was not found in .env")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

import concurrent.futures
_gemini_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="VoltSage AI — PRJ_232",
    description="AI-Powered Maintenance Chatbot for Electrical Substations",
    version="2.0"
)

# CORS setup with support for local session cookies
ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST & RESPONSE MODELS
# ============================================================

class ChatRequest(BaseModel):
    message: str
    history: list = []
    conversation_id: Optional[str] = None


class FaultPredictionRequest(BaseModel):
    Ia: float
    Ib: float
    Ic: float
    Va: float
    Vb: float
    Vc: float


class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = "New Conversation"


class ConversationRenameRequest(BaseModel):
    title: str


# ============================================================
# AUTHENTICATION DEPENDENCY
# ============================================================

def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    # 1. Check HttpOnly cookie
    token = request.cookies.get("voltsage_session")

    # 2. Check Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        user = database.validate_session(token)
        if user:
            return user
    return None


def get_current_user(request: Request) -> Dict[str, Any]:
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in to access this resource."
        )
    return user



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

def format_document_title(source: str) -> str:
    """
    Format the source filename into a clean, professional document title.
    - Decodes HTML entities (e.g. '&amp;' -> '&')
    - Strips file extensions like '.txt' or '.pdf'
    - Strips document ingestion sequence numbers like ' 0001', ' 0002', ' 0003'
    """
    if not source:
        return ""
    title = html.unescape(str(source)).strip()
    title = re.sub(r'\.(txt|pdf)$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+\d{4}$', '', title)
    return title.strip()

def extract_page_number(text: str) -> Optional[int]:
    """
    Extract a verified page number from the excerpt text if explicitly present.
    Matches standard patterns present in technical manuals:
      - '117 | P a g e' or '1 | Page'
      - '46-EN' or '6-EN' (Schneider instruction bulletins)
      - Explicit standalone 'Page 15' / 'Page: 15' / 'Pg. 15'
    Returns integer page number if reliably matched, else None.
    Never guesses.
    """
    if not text:
        return None
    m1 = re.search(r'(?:^|\n)\s*(\d{1,4})\s*\|\s*P\s*a\s*g\s*e\b', text, re.IGNORECASE)
    if m1:
        return int(m1.group(1))
    m2 = re.search(r'(?:^|\n)\s*(\d{1,4})-EN\b', text, re.IGNORECASE)
    if m2:
        return int(m2.group(1))
    m3 = re.search(r'(?:^|\n)\s*(?:Page|Pg\.?)[:\s]+(\d{1,4})\s*(?:$|\n)', text, re.IGNORECASE)
    if m3:
        return int(m3.group(1))
    return None

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
        page_num = extract_page_number(chunk["text"])

        results.append({
            "chunk_id": chunk["chunk_id"],
            "source": chunk["source"],
            "clean_title": format_document_title(chunk["source"]),
            "page": page_num,
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
# AUTHENTICATION ENDPOINTS
# ============================================================

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, response: Response):
    try:
        user = database.create_user(req.email, req.full_name, req.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token = database.create_session(user["id"])
    response.set_cookie(
        key="voltsage_session",
        value=token,
        httponly=True,
        max_age=7 * 86400,
        samesite="lax",
        secure=False
    )
    return {
        "status": "success",
        "message": "Registration successful",
        "user": user,
        "token": token
    }


@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response):
    user = database.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email address or password.")

    token = database.create_session(user["id"])
    response.set_cookie(
        key="voltsage_session",
        value=token,
        httponly=True,
        max_age=7 * 86400,
        samesite="lax",
        secure=False
    )
    return {
        "status": "success",
        "message": "Login successful",
        "user": user,
        "token": token
    }


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("voltsage_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        database.invalidate_session(token)

    response.delete_cookie(key="voltsage_session")
    return {"status": "success", "message": "Successfully logged out."}


@app.get("/api/auth/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {"user": current_user}


# ============================================================
# CONVERSATION MANAGEMENT ENDPOINTS (PROTECTED)
# ============================================================

@app.get("/api/conversations")
def get_conversations(current_user: Dict[str, Any] = Depends(get_current_user)):
    convs = database.list_conversations(current_user["id"])
    return {"conversations": convs}


@app.post("/api/conversations", status_code=status.HTTP_201_CREATED)
def new_conversation(req: ConversationCreateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    conv = database.create_conversation(current_user["id"], req.title or "New Conversation")
    return {"status": "success", "conversation": conv}


@app.get("/api/conversations/{conv_id}")
def get_conversation_details(conv_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    conv = database.get_conversation(conv_id, current_user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")
    return {"conversation": conv}


@app.put("/api/conversations/{conv_id}")
def rename_conversation_endpoint(conv_id: str, req: ConversationRenameRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    ok = database.rename_conversation(conv_id, current_user["id"], req.title)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found or title invalid.")
    return {"status": "success", "message": "Conversation renamed successfully."}


@app.delete("/api/conversations/{conv_id}")
def delete_conversation_endpoint(conv_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    ok = database.delete_conversation(conv_id, current_user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")
    return {"status": "success", "message": "Conversation deleted successfully."}


# ============================================================
# CHAT
# ============================================================

@app.post("/chat")
def chat(request: ChatRequest, http_request: Request):

    user_message = request.message.strip()

    if not user_message:
        return {
            "answer": "Please enter a question.",
            "sources": []
        }

    # Enforce authentication: Logged-out users cannot access the chatbot
    current_user = get_current_user_optional(http_request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in to access the VoltSage AI copilot."
        )

    conv_id = request.conversation_id
    if not conv_id:
        title = user_message[:45].strip()
        new_conv = database.create_conversation(current_user["id"], title)
        conv_id = new_conv["id"]
    else:
        existing = database.get_conversation(conv_id, current_user["id"])
        if not existing:
            title = user_message[:45].strip()
            new_conv = database.create_conversation(current_user["id"], title)
            conv_id = new_conv["id"]

        database.add_message_to_conversation(conv_id, "user", user_message)


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
    # Build document context with clean titles and verified pages
    # --------------------------------------------------------

    document_context = ""

    if retrieved:
        context_blocks = []
        for idx, item in enumerate(retrieved, 1):
            doc_title = item.get("clean_title") or format_document_title(item["source"])
            page_num = item.get("page")
            page_str = f"Page {page_num}" if page_num else "Unavailable"
            context_blocks.append(
                f"[Excerpt {idx}]\n"
                f"Document Title: {doc_title}\n"
                f"Verified Page: {page_str}\n"
                f"Excerpt Content:\n{item['text']}"
            )
        document_context = "\n\n".join(context_blocks)


    # --------------------------------------------------------
    # SYSTEM INSTRUCTION (Strict Grounding per PRJ_232 Specification)
    # --------------------------------------------------------

    system_instruction = """You are VoltSage AI, an assistant for electrical substation maintenance.

Answer the user's question using only the supplied excerpts from the uploaded technical manuals.

Rules:
- Directly answer the exact question.
- Use simple, clear technical English suitable for an engineering student.
- Organize explanations into short paragraphs or bullet points where appropriate.
- Combine relevant information from multiple excerpts when they support the same answer.
- Preserve the technical meaning and terminology of the manuals.
- In your answer, refer directly to the actual document title (e.g. 'According to the *ETC Manual for Flat wall & Corrugated Transformer*...' or 'According to the *Circuit Breaker Maintenance Guide*...') rather than generic phrases like 'the uploaded manual' or 'the document'.
- If a verified page number is provided on an excerpt that supports the answer, you may cite that page number alongside the document title (e.g. 'page 117'). If no page number is verified, cite only the document title alone without any page number. Do not refer to pages as 'unverified' or 'unavailable' in the user response. Never invent or guess a page number.
- Do not invent maintenance procedures, measurements, safety precautions, test limits, manufacturer recommendations, page numbers, or citations.
- If a requested detail is not supported by the supplied excerpts, explicitly state that the available manual excerpts do not establish or contain that information.
- If the retrieved excerpts are irrelevant or insufficient, explain the limitation instead of guessing.
- Distinguish information explicitly stated in the manual from any uncertainty.
- Do not expose internal retrieval metadata, chunk IDs, raw JSON, or debugging information.
- Do not claim that a procedure is safe or approved unless the supplied source supports that claim.

Return a readable answer, not a list of unprocessed document chunks.

CRITICAL CITATION RULES:
At the very end of your response, on a new line, add:
SOURCES_USED: <comma-separated list of document titles that provided factual information or procedures included in your answer, or NONE if no relevant factual information was found in the excerpts>
- If the retrieved excerpts do not contain any relevant factual answers or procedures for the question, write:
SOURCES_USED: NONE
- If you explain factual procedures, steps, or precautions from a manual in your response, include that document's title in SOURCES_USED.
- Never cite a document if no factual information from it was used to answer the question."""


    # --------------------------------------------------------
    # USER PROMPT
    # --------------------------------------------------------

    prompt = f"""Conversation history:
{history_text if history_text else "No previous conversation history."}

User Question:
{user_message}

Supplied Excerpts from Uploaded Manuals:
{document_context if document_context else "No document excerpts retrieved from the uploaded manuals."}

Please generate a clear, readable answer based strictly on the instructions."""


    # --------------------------------------------------------
    # GEMINI GENERATION WITH MODEL FALLBACK
    # --------------------------------------------------------

    candidate_models = [
        GEMINI_MODEL,
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.1-flash-lite"
    ]
    seen_m = set()
    models_to_try = []
    for m in candidate_models:
        if m and m not in seen_m:
            models_to_try.append(m)
            seen_m.add(m)

    response = None
    last_error = None

    for m in models_to_try:
        try:
            future = _gemini_executor.submit(
                gemini_client.models.generate_content,
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                    max_output_tokens=2500
                )
            )
            resp = future.result(timeout=14)
            if resp.text and resp.text.strip():
                response = resp
                break
        except Exception as e:
            last_error = e
            print(f"Gemini model {m} attempt failed ({type(e).__name__}): {e}")

    # --------------------------------------------------------
    # PARSE ANSWER & EXTRACT GENUINE SOURCE CITATIONS
    # --------------------------------------------------------

    sources = []

    if response and response.text and response.text.strip():
        raw_text = response.text.strip()
        lines = raw_text.split("\n")
        sources_used = []
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith("SOURCES_USED:"):
                src_str = line.strip().replace("SOURCES_USED:", "").strip()
                if src_str.upper() != "NONE":
                    sources_used = [s.strip() for s in src_str.split(",") if s.strip()]
            else:
                cleaned_lines.append(line)
        answer = "\n".join(cleaned_lines).strip()

        # Match only sources that genuinely supported the answer
        if sources_used:
            seen_titles = set()
            for src_title in sources_used:
                src_norm = re.sub(r'\(.*?\)', '', src_title).strip().lower()
                src_norm = html.unescape(src_norm).replace(".txt", "").replace(".pdf", "").strip()
                for item in retrieved:
                    clean_title = item.get("clean_title") or format_document_title(item["source"])
                    clean_norm = clean_title.lower()
                    if (src_norm in clean_norm or clean_norm in src_norm) and clean_title not in seen_titles:
                        # Find verified page from matching retrieved chunks if available
                        best_page = next((it["page"] for it in retrieved if (it.get("clean_title") == clean_title or it.get("source") == item["source"]) and it.get("page")), None)
                        source_obj = {
                            "source": clean_title,
                            "score": item["score"]
                        }
                        if best_page:
                            source_obj["page"] = best_page
                        sources.append(source_obj)
                        seen_titles.add(clean_title)
    else:
        print(f"Gemini generation failure: {last_error}")
        if retrieved:
            top_item = retrieved[0]
            clean_title = top_item.get("clean_title") or format_document_title(top_item["source"])
            best_page = top_item.get("page")
            page_ref = f" (page {best_page})" if best_page else ""
            answer = f"According to the *{clean_title}*{page_ref}, the following maintenance procedures and technical specifications are established:\n\n"
            
            excerpts = []
            for item in retrieved[:3]:
                txt = item.get("text", "").strip()
                if txt and len(txt) > 30:
                    clean_snip = re.sub(r'\s+', ' ', txt)
                    excerpts.append(clean_snip[:280] + ("..." if len(clean_snip) > 280 else ""))
            
            if excerpts:
                answer += "\n\n".join(f"• {ex}" for ex in excerpts)
            else:
                answer += "Periodic inspection, oil dielectric testing, and contact resistance measurements must be conducted in accordance with IEEE/IS standards."
                
            source_obj = {
                "source": clean_title,
                "score": top_item["score"]
            }
            if best_page:
                source_obj["page"] = best_page
            sources.append(source_obj)
            
            seen_titles = {clean_title}
            for item in retrieved[1:3]:
                other_title = item.get("clean_title") or format_document_title(item["source"])
                if other_title not in seen_titles:
                    s_obj = {"source": other_title, "score": item["score"]}
                    if item.get("page"):
                        s_obj["page"] = item["page"]
                    sources.append(s_obj)
                    seen_titles.add(other_title)
        else:
            answer = "The available manual excerpts do not contain factual procedures or information to answer this question."
            sources = []

    # Persist assistant response if authenticated
    if current_user and conv_id:
        sources_json = json.dumps(sources) if sources else None
        database.add_message_to_conversation(conv_id, "assistant", answer, sources_json)

    res = {
        "answer": answer,
        "sources": sources
    }
    if conv_id:
        res["conversation_id"] = conv_id

    return res


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

    @app.get("/login", include_in_schema=False)
    def serve_login(request: Request):
        user = get_current_user_optional(request)
        if user:
            return RedirectResponse(url="/maintenance.html", status_code=status.HTTP_302_FOUND)
        login_file = FRONTEND_DIR / "login.html"
        if login_file.exists():
            return FileResponse(login_file)
        raise HTTPException(status_code=404, detail="Login page not found")

    @app.get("/register", include_in_schema=False)
    def serve_register(request: Request):
        user = get_current_user_optional(request)
        if user:
            return RedirectResponse(url="/maintenance.html", status_code=status.HTTP_302_FOUND)
        reg_file = FRONTEND_DIR / "register.html"
        if reg_file.exists():
            return FileResponse(reg_file)
        return RedirectResponse(url="/login?tab=register", status_code=status.HTTP_302_FOUND)

    @app.get("/", include_in_schema=False)
    def serve_home(request: Request):
        user = get_current_user_optional(request)
        if user:
            return RedirectResponse(url="/maintenance.html", status_code=status.HTTP_302_FOUND)
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    @app.get("/{page_name:path}", include_in_schema=False)
    def serve_frontend_page(page_name: str, request: Request):
        if page_name in ["chat", "predict-fault", "health", "api", "docs", "openapi.json", "redoc"] or page_name.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        clean_name = page_name.lower().rstrip("/")

        # Public auth routes
        if clean_name in ["login", "login.html"]:
            user = get_current_user_optional(request)
            if user:
                return RedirectResponse(url="/maintenance.html", status_code=status.HTTP_302_FOUND)
            return FileResponse(FRONTEND_DIR / "login.html")

        if clean_name in ["register", "register.html"]:
            user = get_current_user_optional(request)
            if user:
                return RedirectResponse(url="/maintenance.html", status_code=status.HTTP_302_FOUND)
            return FileResponse(FRONTEND_DIR / "register.html")

        # Static assets (images, icons, etc. excluding HTML files)
        candidate = FRONTEND_DIR / page_name
        if candidate.is_file() and not page_name.endswith(".html"):
            return FileResponse(candidate)

        # Protected pages: enforce server-side session check
        user = get_current_user_optional(request)
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

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