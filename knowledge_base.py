
from pathlib import Path
from pypdf import PdfReader

PROJECT_DIR = Path(__file__).resolve().parent
PDF_PATH = PROJECT_DIR / "Doc" / "Practical_Accounting_AI_Manual.pdf"


def load_manual():
    """Extract readable text from each page of the PDF."""
    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"Accounting manual not found: {PDF_PATH}"
        )

    reader = PdfReader(str(PDF_PATH))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""

        if page_text.strip():
            pages.append({
                "page": page_number,
                "text": page_text
            })

    if not pages:
        raise ValueError(
            "No readable text found in the PDF. "
            "The document may contain scanned pages."
        )

    return pages


def search_manual(question, max_results=5):
    """Find pages that best match the question's keywords."""
    pages = load_manual()

    words = {
        word.lower().strip(".,?!:;()[]{}\"'")
        for word in question.split()
        if len(word.strip(".,?!:;()[]{}\"'")) > 2
    }

    results = []

    for page in pages:
        page_words = {
            word.lower().strip(".,?!:;()[]{}\"'")
            for word in page["text"].split()
        }

        score = len(words & page_words)

        if score:
            results.append({
                "page": page["page"],
                "score": score,
                "text": page["text"]
            })

    results.sort(key=lambda result: result["score"], reverse=True)
    return results[:max_results]
