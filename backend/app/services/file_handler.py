import io

import pdfplumber
from docx import Document
from fastapi import HTTPException


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
    except Exception:
        raise HTTPException(
            status_code=400, detail="Failed to parse PDF. File may be corrupted."
        )
    if not text:
        raise HTTPException(
            status_code=400, detail="PDF contains no extractable text."
        )
    return text


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception:
        raise HTTPException(
            status_code=400, detail="Failed to parse DOCX. File may be corrupted."
        )
    if not text:
        raise HTTPException(
            status_code=400, detail="DOCX contains no extractable text."
        )
    return text


def extract_text(filename: str, file_bytes: bytes) -> str:
    extension = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""

    if extension == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif extension == "docx":
        return extract_text_from_docx(file_bytes)
    elif extension == "txt":
        try:
            text = file_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400, detail="Failed to decode text file."
            )
        if not text:
            raise HTTPException(
                status_code=400, detail="Text file is empty."
            )
        return text
    else:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '.{extension}'. Accepted: .pdf, .docx, .txt",
        )
