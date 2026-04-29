import requests
import fitz
from sqlalchemy.orm import Session
from app.db import crud


def save_document_links(db: Session, notice_id: str, document_links: list[dict]) -> int:
    saved = 0

    for link in document_links or []:
        url = link.get("url")
        if not url:
            continue

        crud.upsert_opportunity_document(
            db,
            {
                "notice_id": notice_id,
                "document_url": url,
                "document_name": link.get("name", ""),
                "document_type": link.get("type", "unknown"),
                "extraction_status": "pending",
            },
        )
        saved += 1

    return saved


def extract_pdf_text_from_url(url: str) -> str:
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()

    if "pdf" not in content_type and not url.lower().endswith(".pdf"):
        raise ValueError("URL does not appear to be a PDF")

    pdf_bytes = response.content
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    text_parts = []

    for page in doc:
        text_parts.append(page.get_text())

    return "\n".join(text_parts).strip()


def process_pending_documents(db: Session, limit: int = 10) -> dict:
    docs = crud.get_pending_documents(db, limit=limit)

    processed = 0
    failed = 0

    for doc in docs:
        try:
            extracted_text = extract_pdf_text_from_url(doc.document_url)

            crud.upsert_opportunity_document(
                db,
                {
                    "notice_id": doc.notice_id,
                    "document_url": doc.document_url,
                    "document_name": doc.document_name,
                    "document_type": doc.document_type,
                    "extracted_text": extracted_text,
                    "extraction_status": "complete",
                    "error_message": "",
                },
            )

            processed += 1

        except Exception as exc:
            crud.upsert_opportunity_document(
                db,
                {
                    "notice_id": doc.notice_id,
                    "document_url": doc.document_url,
                    "document_name": doc.document_name,
                    "document_type": doc.document_type,
                    "extracted_text": "",
                    "extraction_status": "failed",
                    "error_message": str(exc),
                },
            )

            failed += 1

    return {
        "processed": processed,
        "failed": failed,
        "remaining": max(len(docs) - processed - failed, 0),
    }


def get_documents_for_notice(db: Session, notice_id: str) -> list[dict]:
    docs = crud.get_documents_for_notice(db, notice_id)

    return [
        {
            "notice_id": d.notice_id,
            "document_url": d.document_url,
            "document_name": d.document_name,
            "document_type": d.document_type,
            "extraction_status": d.extraction_status,
            "error_message": d.error_message,
            "text_preview": (d.extracted_text or "")[:1000],
            "text_length": len(d.extracted_text or ""),
        }
        for d in docs
    ]


def get_combined_document_text(db, notice_id: str, max_chars: int = 12000) -> str:
    from app.db import crud

    docs = crud.get_documents_for_notice(db, notice_id)

    text = ""

    for doc in docs:
        if doc.extraction_status == "complete" and doc.extracted_text:
            text += f"\n\nDOCUMENT: {doc.document_name}\n"
            text += doc.extracted_text

    return text[:max_chars]