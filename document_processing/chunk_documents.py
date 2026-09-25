import os
import json


# ============================================================
# PRJ_232 - DOCUMENT CHUNKING
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

PROCESSED_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed"
)

CHUNKS_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed"
)

OUTPUT_FILE = os.path.join(
    CHUNKS_DIR,
    "document_chunks.json"
)


# ------------------------------------------------------------
# SETTINGS
# ------------------------------------------------------------

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


print("=" * 70)
print("PRJ_232 - MAINTENANCE DOCUMENT CHUNKING")
print("=" * 70)


# ------------------------------------------------------------
# FIND EXTRACTED TEXT FILES
# ------------------------------------------------------------

text_files = [
    file
    for file in os.listdir(PROCESSED_DIR)
    if file.lower().endswith(".txt")
    and file != "all_maintenance_documents.txt"
]


if not text_files:

    print("\nNo extracted text files found.")

    raise SystemExit


print(
    f"\nText documents found: {len(text_files)}"
)


# ------------------------------------------------------------
# CHUNK FUNCTION
# ------------------------------------------------------------

def create_chunks(text, chunk_size, overlap):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk_text = text[start:end].strip()

        if chunk_text:

            chunks.append(chunk_text)

        start = end - overlap

    return chunks


# ------------------------------------------------------------
# PROCESS DOCUMENTS
# ------------------------------------------------------------

all_chunks = []

chunk_id = 1


for text_file in text_files:

    file_path = os.path.join(
        PROCESSED_DIR,
        text_file
    )

    print("\n" + "-" * 70)

    print(
        f"Processing: {text_file}"
    )


    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        text = file.read()


    document_chunks = create_chunks(
        text,
        CHUNK_SIZE,
        CHUNK_OVERLAP
    )


    print(
        f"Characters: {len(text)}"
    )

    print(
        f"Chunks created: {len(document_chunks)}"
    )


    # --------------------------------------------------------
    # STORE EACH CHUNK
    # --------------------------------------------------------

    for chunk_text in document_chunks:

        chunk = {
            "chunk_id": chunk_id,
            "source": text_file,
            "text": chunk_text
        }

        all_chunks.append(chunk)

        chunk_id += 1


# ------------------------------------------------------------
# SAVE CHUNKS
# ------------------------------------------------------------

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        all_chunks,
        file,
        indent=2,
        ensure_ascii=False
    )


# ------------------------------------------------------------
# FINAL SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("DOCUMENT CHUNKING COMPLETE")
print("=" * 70)

print(
    f"\nTotal chunks: {len(all_chunks)}"
)

print(
    f"Chunk size: {CHUNK_SIZE} characters"
)

print(
    f"Chunk overlap: {CHUNK_OVERLAP} characters"
)

print(
    f"\nSaved to:"
)

print(OUTPUT_FILE)

print("\n" + "=" * 70)