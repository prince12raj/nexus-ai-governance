"""
ingestion/parser.py — Unified file-parsing dispatcher.
"""
from __future__ import annotations

import io
import json
from typing import Any

import pandas as pd

from config.logging_config import get_logger

logger = get_logger("nexus.ingestion.parser")


def extract_text(uploaded_file: Any) -> str:
    """
    Extract plain text from any supported file type.

    Supports: .pdf, .docx, .txt, .csv, .json
    Falls back to UTF-8 decode for unknown types.
    """
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".txt"):
            return uploaded_file.read().decode("utf-8", errors="replace")

        elif name.endswith(".pdf"):
            return _read_pdf(uploaded_file)

        elif name.endswith(".docx"):
            return _read_docx(uploaded_file)

        elif name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(uploaded_file.read()))
            return df.to_string()

        elif name.endswith(".json"):
            data = json.loads(uploaded_file.read())
            return json.dumps(data, indent=2)

        else:
            return uploaded_file.read().decode("utf-8", errors="replace")

    except Exception as exc:
        logger.error("File extraction error for %s: %s", name, exc)
        return f"[Error extracting file: {exc}]"


def _read_pdf(uploaded_file: Any) -> str:
    try:
        import PyPDF2  # type: ignore
        reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        logger.warning("PyPDF2 not installed — falling back to raw decode.")
        return uploaded_file.read().decode("utf-8", errors="replace")


def _read_docx(uploaded_file: Any) -> str:
    try:
        import docx  # type: ignore
        doc = docx.Document(io.BytesIO(uploaded_file.read()))
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        logger.warning("python-docx not installed — falling back to raw decode.")
        return uploaded_file.read().decode("utf-8", errors="replace")
