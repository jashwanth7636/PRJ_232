import os
from pypdf import PdfReader


# ============================================================
# PRJ_232 - PDF TEXT EXTRACTION
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

DOCUMENTS_DIR = os.path.join(
    PROJECT_ROOT,
    "documents"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


print("=" * 70)
print("PRJ_232 - MAINTENANCE PDF TEXT EXTRACTION")
print("=" * 70)


# ------------------------------------------------------------
# FIND PDF FILES
# ------------------------------------------------------------

pdf_files = [
    file
    for file in os.listdir(DOCUMENTS_DIR)
    if file.lower().endswith(".pdf")
]


if not pdf_files:
    print("\nNo PDF files found.")
    print("Please put your maintenance PDFs inside:")
    print(DOCUMENTS_DIR)
    raise SystemExit


print(f"\nPDF files found: {len(pdf_files)}")


# ------------------------------------------------------------
# EXTRACT TEXT FROM EACH PDF
# ------------------------------------------------------------

all_text = ""

for pdf_file in pdf_files:

    pdf_path = os.path.join(
        DOCUMENTS_DIR,
        pdf_file
    )

    print("\n" + "-" * 70)
    print(f"Processing: {pdf_file}")

    reader = PdfReader(pdf_path)

    print(f"Pages: {len(reader.pages)}")

    document_text = ""

    for page_number, page in enumerate(reader.pages, start=1):

        try:
            text = page.extract_text()

            if text:
                document_text += text + "\n"

        except Exception as error:

            print(
                f"Warning: Could not read page "
                f"{page_number}: {error}"
            )


    # --------------------------------------------------------
    # SAVE INDIVIDUAL TEXT FILE
    # --------------------------------------------------------

    text_file_name = (
        os.path.splitext(pdf_file)[0]
        + ".txt"
    )

    text_file_path = os.path.join(
        OUTPUT_DIR,
        text_file_name
    )

    with open(
        text_file_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(document_text)


    # --------------------------------------------------------
    # DISPLAY INFORMATION
    # --------------------------------------------------------

    character_count = len(document_text)

    word_count = len(
        document_text.split()
    )

    print(
        f"Extracted characters: {character_count}"
    )

    print(
        f"Extracted words     : {word_count}"
    )

    print(
        f"Saved text          : {text_file_path}"
    )


    # Add document information to combined text

    all_text += (
        "\n\n"
        + "=" * 70
        + "\n"
        + f"SOURCE DOCUMENT: {pdf_file}"
        + "\n"
        + "=" * 70
        + "\n\n"
        + document_text
    )


# ------------------------------------------------------------
# SAVE COMBINED TEXT
# ------------------------------------------------------------

combined_file = os.path.join(
    OUTPUT_DIR,
    "all_maintenance_documents.txt"
)

with open(
    combined_file,
    "w",
    encoding="utf-8"
) as file:

    file.write(all_text)


# ------------------------------------------------------------
# FINAL SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("PDF EXTRACTION COMPLETE")
print("=" * 70)

print(
    f"\nDocuments processed: {len(pdf_files)}"
)

print(
    f"Combined text file: {combined_file}"
)

print("\n" + "=" * 70)