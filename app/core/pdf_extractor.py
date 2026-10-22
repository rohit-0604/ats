"""
ATS v8 — PDF Extractor
Validates, extracts text from PDFs, and splits into chunks.
CHUNK_OVERLAP is hardcoded to 0 — see config.py for why.

Extraction strategy (in order):
  1. pdfplumber text extraction (all text PDFs)
  2. pdfplumber table extraction — tables converted to pipe-delimited rows
  3. OCR fallback via pdf2image + pytesseract (scanned PDFs only)
"""

from __future__ import annotations
import hashlib
import logging
from pathlib import Path
from typing import Optional
import pdfplumber

from app.config import CHUNK_SIZE, CHUNK_OVERLAP

log = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF"


def validate_pdf(path: str | Path) -> tuple[bool, str]:
    """
    Checks file extension AND magic bytes.
    Returns (ok, error_message).
    Rejects: non-.pdf extensions, renamed files, Word docs, images.
    """
    p = Path(path)
    if not p.exists():
        return False, f"File not found: {path}"
    if p.suffix.lower() != ".pdf":
        return False, (
            f"File extension is not .pdf: {p.suffix!r} — only .pdf files accepted. "
            "Word docs, images, and other formats must be converted to PDF first."
        )
    with open(p, "rb") as f:
        header = f.read(4)
    if header != PDF_MAGIC:
        return False, (
            f"File is not a valid PDF (magic bytes: {header!r}). "
            "A Word doc, image, or other file renamed to .pdf will be rejected here."
        )
    return True, ""


def extract_text(path: str | Path) -> str:
    """
    Extract all text from PDF using pdfplumber.
    Tables extracted separately as pipe-delimited rows so the LLM
    sees structured table data rather than garbled merged columns.
    """
    p = Path(path)
    pages = []

    with pdfplumber.open(p) as pdf:
        for page in pdf.pages:
            parts = []

            # Body text (paragraphs, headings, captions)
            text = page.extract_text()
            if text and text.strip():
                parts.append(text.strip())

            # Tables — extract separately, convert to pipe-delimited rows
            try:
                tables = page.extract_tables()
                for table in (tables or []):
                    rows = []
                    for row in table:
                        if row:
                            clean = [str(cell).strip() if cell else "" for cell in row]
                            if any(c for c in clean):
                                rows.append(" | ".join(clean))
                    if rows:
                        parts.append("TABLE:\n" + "\n".join(rows))
            except Exception as e:
                log.debug(f"Table extraction failed on page (non-critical): {e}")

            if parts:
                pages.append("\n\n".join(parts))

    full_text = "\n\n".join(pages)
    log.info(f"PDF extracted: {len(pages)} pages, {len(full_text):,} chars from {p.name}")
    return full_text


def _ocr_fallback(path: str | Path) -> str:
    """
    OCR fallback for scanned PDFs. Only called when pdfplumber returns empty text.
    Requires: pip install pdf2image pytesseract
    Requires: Tesseract installed on system.
      Windows: https://github.com/UB-Mannheim/tesseract/wiki
      Linux:   sudo apt install tesseract-ocr
      macOS:   brew install tesseract
    Optional .env: TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        log.error(
            "OCR fallback requires pdf2image and pytesseract.\n"
            "  pip install pdf2image pytesseract\n"
            "  Then install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
        )
        return ""

    import os
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    try:
        log.info("OCR: converting PDF to images at 200 DPI...")
        images = convert_from_path(str(path), dpi=200)
        pages = []
        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, lang="eng")
            if text.strip():
                pages.append(text.strip())
            log.debug(f"OCR: page {i+1}/{len(images)} -> {len(text)} chars")
        result = "\n\n".join(pages)
        log.info(f"OCR fallback: extracted {len(result):,} chars from {len(images)} pages")
        return result
    except Exception as e:
        log.error(f"OCR fallback failed: {e}")
        return ""


def sha256_of_file(path: str | Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """
    Split text into chunks of ~chunk_size characters.
    CHUNK_OVERLAP = 0 (hardcoded). Splits on paragraph boundary first,
    then sentence boundary, then space — never mid-word.
    """
    assert CHUNK_OVERLAP == 0, "CHUNK_OVERLAP must be 0 — do not change"

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        para_break = text.rfind("\n\n", start, end)
        if para_break > start:
            chunks.append(text[start:para_break].strip())
            start = para_break + 2
            continue
        line_break = text.rfind("\n", start, end)
        if line_break > start:
            chunks.append(text[start:line_break].strip())
            start = line_break + 1
            continue
        space = text.rfind(" ", start, end)
        if space > start:
            chunks.append(text[start:space].strip())
            start = space + 1
            continue
        chunks.append(text[start:end].strip())
        start = end

    return [c for c in chunks if c]


def load_pdf(path: str | Path) -> tuple[str, list[str], str]:
    """
    Validates, extracts, chunks a PDF.
    Returns: (full_text, chunks, sha256_hex)
    Raises ValueError on invalid PDF or if no text can be extracted.
    """
    ok, err = validate_pdf(path)
    if not ok:
        raise ValueError(err)

    sha = sha256_of_file(path)
    full_text = extract_text(path)

    # OCR fallback for scanned PDFs
    if not full_text.strip():
        log.warning(
            f"PDF '{Path(path).name}' returned no text — likely scanned. "
            "Attempting OCR fallback..."
        )
        full_text = _ocr_fallback(path)

    if not full_text.strip():
        raise ValueError(
            f"No text could be extracted from '{Path(path).name}'.\n"
            "If this is a scanned PDF:\n"
            "  1. Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  2. pip install pdf2image pytesseract\n"
            "  3. Optionally set TESSERACT_CMD in .env"
        )

    chunks = chunk_text(full_text)
    log.info(
        f"PDF loaded: {len(chunks)} chunks "
        f"(size={CHUNK_SIZE}, overlap=0) sha256={sha[:16]}..."
    )
    return full_text, chunks, sha
