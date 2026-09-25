import json
import ollama
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ---------------------------------------------------------
# 1. Load maintenance document chunks
# ---------------------------------------------------------

CHUNKS_FILE = Path("data/processed/document_chunks.json")

with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
    chunks = json.load(file)

print(f"Loaded {len(chunks)} document chunks.")


# ---------------------------------------------------------
# 2. Prepare usable chunks
# ---------------------------------------------------------

usable_chunks = []

for chunk in chunks:

    text = " ".join(chunk["text"].split())

    if len(text) >= 250:

        usable_chunks.append({
            "chunk_id": chunk["chunk_id"],
            "source": chunk["source"],
            "text": text
        })


# ---------------------------------------------------------
# 3. Build TF-IDF search index
# ---------------------------------------------------------

texts = [
    chunk["text"]
    for chunk in usable_chunks
]

vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=30000
)

document_vectors = vectorizer.fit_transform(texts)

print(f"Search index created with {len(usable_chunks)} usable chunks.")


# ---------------------------------------------------------
# 4. Retrieve relevant documents
# ---------------------------------------------------------

def retrieve_documents(question, top_k=5):

    question_vector = vectorizer.transform([question])

    scores = cosine_similarity(
        question_vector,
        document_vectors
    )[0]

    top_indices = scores.argsort()[-top_k:][::-1]

    results = []

    for index in top_indices:

        result = usable_chunks[index].copy()

        result["score"] = float(scores[index])

        results.append(result)

    return results


# ---------------------------------------------------------
# 5. Generate grounded answer using Llama
# ---------------------------------------------------------

def generate_answer(question, retrieved_documents):

    context_parts = []

    for i, document in enumerate(retrieved_documents, start=1):

        context_parts.append(
            f"""
[Source {i}]
Manual: {document["source"]}
Chunk ID: {document["chunk_id"]}

{document["text"]}
"""
        )

    context = "\n".join(context_parts)

    prompt = f"""
You are an AI-powered electrical substation maintenance assistant.

Answer the user's question using the maintenance information provided
below.

Rules:

1. Use the provided maintenance documents as the primary source.
2. Do not invent technical procedures or safety requirements.
3. If the documents do not contain enough information, say so clearly.
4. Give a clear answer suitable for an engineering student.
5. Do not claim that a procedure is safe unless the provided information
   supports it.
6. Mention the relevant manual source in the answer when appropriate.

Maintenance information:

{context}

User question:

{question}

Provide a concise, practical answer.
"""

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]


# ---------------------------------------------------------
# 6. Run RAG test
# ---------------------------------------------------------

question = input(
    "\nEnter a maintenance question: "
)

retrieved = retrieve_documents(question)


# ---------------------------------------------------------
# 7. Display retrieved sources
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("RETRIEVED MAINTENANCE SOURCES")
print("=" * 70)

for i, document in enumerate(retrieved, start=1):

    print(f"\n--- Source {i} ---")
    print(f"Manual   : {document['source']}")
    print(f"Chunk ID : {document['chunk_id']}")
    print(f"Score    : {document['score']:.4f}")
    print(f"Content  : {document['text'][:400]}...")


# ---------------------------------------------------------
# 8. Generate answer
# ---------------------------------------------------------

answer = generate_answer(
    question,
    retrieved
)


# ---------------------------------------------------------
# 9. Display final answer
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("LLAMA 3.2 3B - GROUNDED ANSWER")
print("=" * 70)

print(answer)


print("\n" + "=" * 70)
print("SOURCES USED")
print("=" * 70)

for document in retrieved:

    print(
        f"- {document['source']} "
        f"(Chunk {document['chunk_id']})"
    )