import os
import json
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# PRJ_232 - IMPROVED LOCAL MAINTENANCE DOCUMENT SEARCH
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

CHUNKS_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed",
    "document_chunks.json"
)

TOP_K = 5


print("=" * 70)
print("PRJ_232 - LOCAL MAINTENANCE DOCUMENT SEARCH")
print("=" * 70)


# ------------------------------------------------------------
# LOAD CHUNKS
# ------------------------------------------------------------

print("\nLoading document chunks...")

with open(
    CHUNKS_FILE,
    "r",
    encoding="utf-8"
) as file:

    chunks = json.load(file)


print(
    f"Original chunks loaded: {len(chunks)}"
)


# ------------------------------------------------------------
# CLEAN TEXT
# ------------------------------------------------------------

def clean_text(text):

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = re.sub(
        r"Page\s+\d+",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text.strip()


# ------------------------------------------------------------
# CLEAN CHUNKS
# ------------------------------------------------------------

cleaned_chunks = []

for chunk in chunks:

    text = clean_text(
        chunk["text"]
    )

    # Ignore extremely short chunks
    if len(text) < 250:
        continue

    cleaned_chunks.append({
        "chunk_id": chunk["chunk_id"],
        "source": chunk["source"],
        "text": text
    })


chunks = cleaned_chunks


print(
    f"Usable chunks: {len(chunks)}"
)


# ------------------------------------------------------------
# CREATE TEXT LIST
# ------------------------------------------------------------

documents = [
    chunk["text"]
    for chunk in chunks
]


# ------------------------------------------------------------
# CREATE TF-IDF INDEX
# ------------------------------------------------------------

print("\nBuilding search index...")

vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=30000
)

document_vectors = vectorizer.fit_transform(
    documents
)


print("Search index created successfully.")


# ------------------------------------------------------------
# SEARCH FUNCTION
# ------------------------------------------------------------

def search_documents(
    query,
    top_k=TOP_K
):

    query_vector = vectorizer.transform(
        [query]
    )

    similarities = cosine_similarity(
        query_vector,
        document_vectors
    )[0]

    ranked_indices = similarities.argsort()[::-1]

    results = []

    for index in ranked_indices:

        score = similarities[index]

        # Don't return completely unrelated results
        if score <= 0:
            continue

        results.append({
            "chunk_id": chunks[index]["chunk_id"],
            "source": chunks[index]["source"],
            "score": float(score),
            "text": chunks[index]["text"]
        })

        if len(results) >= top_k:
            break

    return results


# ------------------------------------------------------------
# INTERACTIVE SEARCH
# ------------------------------------------------------------

while True:

    print("\n" + "-" * 70)

    query = input(
        "Enter maintenance question "
        "(type 'exit' to stop): "
    ).strip()


    if query.lower() == "exit":

        print("\nSearch program closed.")

        break


    if not query:

        print("Please enter a question.")

        continue


    results = search_documents(
        query
    )


    print("\n" + "=" * 70)
    print("TOP SEARCH RESULTS")
    print("=" * 70)


    if not results:

        print(
            "\nNo relevant document section found."
        )

        continue


    for number, result in enumerate(
        results,
        start=1
    ):

        print(
            f"\nRESULT {number}"
        )

        print(
            f"Chunk ID : {result['chunk_id']}"
        )

        print(
            f"Source   : {result['source']}"
        )

        print(
            f"Score    : {result['score']:.4f}"
        )

        print("\nText:")

        print(
            result["text"]
        )


print("\n" + "=" * 70)