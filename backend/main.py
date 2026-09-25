import os
import json
from pathlib import Path

import joblib
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from google import genai


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env", override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY was not found in .env")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = "gemini-3.5-flash-lite"


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
# LOAD DOCUMENT CHUNKS
# ============================================================

CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "document_chunks.json"

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    document_chunks = json.load(f)


# ============================================================
# PREPARE DOCUMENT SEARCH
# ============================================================

def clean_text(text):
    return " ".join(str(text).split())


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


vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=30000
)

tfidf_matrix = vectorizer.fit_transform(documents)


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

@app.get("/")
def root():

    return {
        "project": "PRJ_232",
        "name": "AI-Powered Maintenance Chatbot",
        "status": "running"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "gemini": "connected",
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

    response = gemini_client.models.generate_content(

        model=GEMINI_MODEL,

        contents=prompt,

        config={
            "system_instruction": system_instruction,
            "temperature": 0.2,
            "max_output_tokens": 300
        }
    )


    answer = response.text.strip()


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

    features = np.array([
        [
            request.Ia,
            request.Ib,
            request.Ic,
            request.Va,
            request.Vb,
            request.Vc
        ]
    ])

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