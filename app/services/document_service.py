import requests
import fitz
from sqlalchemy.orm import Session
from fastapi import UploadFile

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

    doc = fitz.open(stream=response.content, filetype="pdf")

    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())

    return "\n".join(text_parts).strip()


def extract_pdf_text_from_upload(file: UploadFile) -> str:
    pdf_bytes = file.file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())

    return "\n".join(text_parts).strip()


def process_document_rows(db: Session, docs) -> dict:
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
        "attempted": len(docs),
    }


def process_pending_documents(db: Session, limit: int = 10) -> dict:
    docs = crud.get_pending_documents(db, limit=limit)
    return process_document_rows(db, docs)


def process_documents_for_reviewed_opportunities(db: Session, profile_id: int, limit: int = 10) -> dict:
    reviews = crud.get_reviews_for_profile(db, profile_id)

    target_notice_ids = [
        review.notice_id
        for review in reviews
        if review.disposition in ["Good Fit", "Maybe"]
    ]

    docs = crud.get_pending_documents_for_notice_ids(
        db=db,
        notice_ids=target_notice_ids,
        limit=limit,
    )

    result = process_document_rows(db, docs)
    result["reviewed_notice_ids"] = target_notice_ids
    return result


def upload_and_extract_document(db: Session, notice_id: str, file: UploadFile) -> dict:
    try:
        extracted_text = extract_pdf_text_from_upload(file)

        document_url = f"manual_upload://{notice_id}/{file.filename}"

        doc = crud.upsert_opportunity_document(
            db,
            {
                "notice_id": notice_id,
                "document_url": document_url,
                "document_name": file.filename,
                "document_type": "manual_pdf_upload",
                "extracted_text": extracted_text,
                "extraction_status": "complete",
                "error_message": "",
            },
        )

        return {
            "status": "uploaded_and_extracted",
            "notice_id": notice_id,
            "document_name": file.filename,
            "text_length": len(extracted_text),
            "document_id": doc.id,
        }

    except Exception as exc:
        document_url = f"manual_upload://{notice_id}/{file.filename}"

        crud.upsert_opportunity_document(
            db,
            {
                "notice_id": notice_id,
                "document_url": document_url,
                "document_name": file.filename,
                "document_type": "manual_pdf_upload",
                "extracted_text": "",
                "extraction_status": "failed",
                "error_message": str(exc),
            },
        )

        return {
            "status": "failed",
            "notice_id": notice_id,
            "document_name": file.filename,
            "error": str(exc),
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


def get_combined_document_text(db: Session, notice_id: str, max_chars: int = 12000) -> str:
    docs = crud.get_documents_for_notice(db, notice_id)

    text = ""

    for doc in docs:
        if doc.extraction_status == "complete" and doc.extracted_text:
            text += f"\n\nDOCUMENT: {doc.document_name}\n"
            text += doc.extracted_text

    return text[:max_chars]