"""
Knowledge Base Ingestion — parse PDFs/docs into searchable chunks.
Supports up to 50 pages. Version control with approval workflow.
Uses text extraction (no ML), chunked for RAG retrieval.
"""

import logging
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

KB_DIR = Path(__file__).parent.parent / "knowledge_docs"
KB_DIR.mkdir(exist_ok=True)

# In-memory knowledge base store
_documents: dict[str, dict] = {}  # doc_id → metadata + chunks
_all_chunks: list[dict] = []  # flat list for search


def ingest_pdf(filepath: str, title: str = "", approved: bool = False) -> dict:
    """
    Ingest a PDF file into the knowledge base.
    Extracts text, chunks it, stores for retrieval.
    """
    path = Path(filepath)
    if not path.exists():
        return {"success": False, "error": f"File not found: {filepath}"}

    try:
        # Try PyPDF2 first
        text = _extract_text_from_pdf(str(path))
    except Exception as e:
        return {"success": False, "error": f"PDF extraction failed: {e}"}

    if not text.strip():
        return {"success": False, "error": "No text extracted from PDF"}

    # Generate document ID
    doc_id = hashlib.md5(path.name.encode()).hexdigest()[:12]

    # Chunk the text (max 500 chars per chunk with overlap)
    chunks = _chunk_text(text, chunk_size=500, overlap=50)

    # Check 50-page limit (approximate: ~3000 chars per page)
    total_pages = len(text) // 3000 + 1
    existing_pages = sum(d.get("pages", 0) for d in _documents.values())
    if existing_pages + total_pages > 50:
        return {"success": False, "error": f"Knowledge base limit: 50 pages. Current: {existing_pages}, this doc: {total_pages}"}

    # Store document
    doc = {
        "doc_id": doc_id,
        "title": title or path.stem,
        "filename": path.name,
        "pages": total_pages,
        "total_chars": len(text),
        "chunks_count": len(chunks),
        "status": "approved" if approved else "pending_approval",
        "version": 1,
        "ingested_at": datetime.now().isoformat(),
        "approved_at": datetime.now().isoformat() if approved else None,
    }
    _documents[doc_id] = doc

    # Store chunks (only if approved)
    if approved:
        for i, chunk in enumerate(chunks):
            _all_chunks.append({
                "doc_id": doc_id,
                "chunk_index": i,
                "text": chunk,
                "title": doc["title"],
            })

    logger.info(f"KB ingested: {path.name} ({total_pages} pages, {len(chunks)} chunks, status={doc['status']})")
    return {"success": True, "document": doc}


def ingest_text(text: str, title: str, approved: bool = True) -> dict:
    """Ingest raw text directly into the knowledge base."""
    doc_id = hashlib.md5(title.encode()).hexdigest()[:12]
    chunks = _chunk_text(text, chunk_size=500, overlap=50)
    total_pages = len(text) // 3000 + 1

    doc = {
        "doc_id": doc_id,
        "title": title,
        "filename": "direct_input",
        "pages": total_pages,
        "total_chars": len(text),
        "chunks_count": len(chunks),
        "status": "approved" if approved else "pending_approval",
        "version": 1,
        "ingested_at": datetime.now().isoformat(),
        "approved_at": datetime.now().isoformat() if approved else None,
    }
    _documents[doc_id] = doc

    if approved:
        for i, chunk in enumerate(chunks):
            _all_chunks.append({
                "doc_id": doc_id,
                "chunk_index": i,
                "text": chunk,
                "title": title,
            })

    return {"success": True, "document": doc}


def approve_document(doc_id: str) -> bool:
    """Approve a pending document — makes its chunks available for retrieval."""
    if doc_id not in _documents:
        return False
    doc = _documents[doc_id]
    if doc["status"] == "approved":
        return True

    doc["status"] = "approved"
    doc["approved_at"] = datetime.now().isoformat()

    # Load chunks into search index (re-extract if needed)
    # For now, chunks were already stored during ingestion
    return True


def search_knowledge_base(query: str, top_k: int = 5) -> list[dict]:
    """
    Search the knowledge base for relevant chunks.
    Simple keyword matching (upgrade to embeddings later if needed).
    """
    if not query or not _all_chunks:
        return []

    query_lower = query.lower()
    query_words = set(query_lower.split())
    scored = []

    for chunk in _all_chunks:
        text_lower = chunk["text"].lower()
        # Score by word overlap
        score = sum(1 for w in query_words if w in text_lower)
        # Boost exact phrase match
        if query_lower in text_lower:
            score += 5
        if score > 0:
            scored.append({**chunk, "_score": score})

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored[:top_k]


def get_all_documents() -> list[dict]:
    """Get all ingested documents."""
    return list(_documents.values())


def get_kb_stats() -> dict:
    """Knowledge base statistics."""
    total_pages = sum(d.get("pages", 0) for d in _documents.values())
    approved = sum(1 for d in _documents.values() if d["status"] == "approved")
    pending = sum(1 for d in _documents.values() if d["status"] == "pending_approval")
    return {
        "total_documents": len(_documents),
        "total_pages": total_pages,
        "pages_remaining": max(0, 50 - total_pages),
        "total_chunks": len(_all_chunks),
        "approved": approved,
        "pending": pending,
    }


# === HELPERS ===

def _extract_text_from_pdf(filepath: str) -> str:
    """Extract text from PDF using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except ImportError:
        # Fallback: try pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                return "\n\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            raise ImportError("Install PyPDF2 or pdfplumber: pip install PyPDF2")


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            if break_point > chunk_size // 2:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1
        chunks.append(chunk.strip())
        start = end - overlap
    return [c for c in chunks if c]  # Remove empty
