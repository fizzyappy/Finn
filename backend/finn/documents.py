"""Primary documents (results PDFs, concall transcripts, annual reports):
download once, keep the file, extract text page by page.

The extracted text is kept exactly as the PDF gives it (no cleaning), because
every quote FINN shows must be verified word-for-word against it. A separate
normalised form (`normalise_ws`) exists only for searching.

Scanned PDFs (images, no text layer) are detected and flagged rather than
silently returning nothing.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from . import config, http
from .store import store


class NotAPdf(ValueError):
    pass


def allowed(url: str) -> bool:
    """Exchange-hosted document (the only place we accept a PDF from)."""
    u = urlparse(url)
    host = (u.hostname or "").lower()
    return u.scheme == "https" and any(host == h or host.endswith("." + h) for h in config.DOC_HOSTS)


def is_screener_redirect(url: str) -> bool:
    u = urlparse(url)
    return u.scheme == "https" and u.hostname == "www.screener.in" and u.path.startswith("/company/source/")


def _download(url: str, trusted: frozenset[str] = frozenset()) -> tuple[bytes, str]:
    """`trusted` = links listed in the company's own documents (e.g. its investor site).
    Anything else must be exchange-hosted."""
    company_doc = url in trusted and urlparse(url).scheme == "https"
    if not (allowed(url) or is_screener_redirect(url) or company_doc):
        raise ValueError(f"documents are only fetched from exchange sites {config.DOC_HOSTS} "
                         f"or the company's own listed documents: {url}")
    r = http.get(url, timeout=120, stream=True,
                 headers={"Referer": "https://www.bseindia.com/", "Accept": "application/pdf,*/*"})
    same_host = urlparse(r.url).hostname == urlparse(url).hostname
    if not (allowed(r.url) or (company_doc and same_host)):
        if hasattr(r, "close"):
            r.close()
        raise ValueError(f"link did not lead to an exchange or company document (ended at {urlparse(r.url).hostname})")
    buf = io.BytesIO()
    for chunk in r.iter_content(256 * 1024):
        buf.write(chunk)
        if buf.tell() > config.MAX_PDF_BYTES:
            raise ValueError(f"document larger than {config.MAX_PDF_BYTES // 2**20} MB, skipped")
    data = buf.getvalue()
    if not data.startswith(b"%PDF-"):
        raise NotAPdf(f"not a PDF ({r.headers.get('content-type', '?')}, {len(data)} bytes)")
    return data, r.headers.get("content-type", "application/pdf")


def fetch_pdf(url: str, refresh: bool = False, trusted: frozenset[str] = frozenset()) -> dict:
    """Download (or reuse) a PDF. Returns its record: path, sha256, size."""
    rec = store().get_document(url)
    if rec and not refresh and rec.get("path") and Path(rec["path"]).exists():
        return rec
    data, ctype = _download(url, trusted)
    sha = hashlib.sha256(data).hexdigest()
    config.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.DOCS_DIR / f"{sha}.pdf"
    if not path.exists():
        path.write_bytes(data)
    rec = {"url": url, "sha256": sha, "path": str(path), "bytes": len(data), "content_type": ctype,
           "pages": None, "text_chars": None, "status": "downloaded"}
    store().put_document(rec)
    return rec


def extract_pages(pdf_bytes: bytes) -> tuple[list[str], str]:
    """Text of each page. pypdf first; pdfplumber if pypdf finds almost nothing."""
    from pypdf import PdfReader

    pages: list[str] = []
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = [(p.extract_text() or "") for p in reader.pages]
        method = "pypdf"
    except Exception:  # noqa: BLE001 - damaged PDFs: try the other extractor
        method = "pypdf-failed"
    if not pages or sum(len(p.strip()) for p in pages) < 50 * max(1, len(pages)):
        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                alt = [(p.extract_text() or "") for p in pdf.pages]
            if sum(map(len, alt)) > sum(map(len, pages)):
                pages, method = alt, "pdfplumber"
        except Exception:  # noqa: BLE001
            pass
    return pages, method


def get_text(url: str, refresh: bool = False, trusted: frozenset[str] | set[str] = frozenset()) -> dict:
    """Download if needed, extract text (cached next to the PDF), return pages + facts."""
    rec = fetch_pdf(url, refresh=refresh, trusted=frozenset(trusted))
    pdf_path = Path(rec["path"])
    txt_path = pdf_path.with_suffix(".pages.json")
    if txt_path.exists() and not refresh:
        cached = json.loads(txt_path.read_text(encoding="utf-8"))
        pages, method = cached["pages"], cached["method"]
    else:
        pages, method = extract_pages(pdf_path.read_bytes())
        txt_path.write_text(json.dumps({"url": url, "method": method, "pages": pages}, ensure_ascii=False),
                            encoding="utf-8")
    chars = sum(len(p) for p in pages)
    empty = sum(1 for p in pages if len(p.strip()) < 20)
    status = "ok"
    if pages and empty / len(pages) > 0.6:
        status = "scanned_needs_ocr"
    elif not pages:
        status = "unreadable"
    store().put_document({**rec, "pages": len(pages), "text_chars": chars, "status": status})
    return {"url": url, "sha256": rec["sha256"], "path": str(pdf_path), "bytes": rec["bytes"],
            "pages": pages, "page_count": len(pages), "text_chars": chars, "empty_pages": empty,
            "method": method, "status": status}


def normalise_ws(s: str) -> str:
    """For searching only: collapse whitespace and join words split across lines."""
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
    return re.sub(r"\s+", " ", s).strip()


_QUOTE_CHARS = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


def quote_key(s: str) -> str:
    """Comparison form for quote checks: case, curly quotes and dashes normalised, and
    ALL whitespace removed. PDF text often breaks words with stray spaces ('gui dance'),
    so spacing is ignored; every other character must match."""
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s or "").translate(_QUOTE_CHARS).lower()
    return re.sub(r"\s+", "", s)


def find_quote(pages: list[str], quote: str) -> int | None:
    """1-based page number where `quote` appears word for word (spacing ignored), else None.
    A quote that runs over a page break is found on the page where it starts.
    Used to verify every quote against its source before it is shown."""
    target = quote_key(quote)
    if len(target) < 4:
        return None
    keys = [quote_key(p) for p in pages]
    for i, k in enumerate(keys):
        if target in k:
            return i + 1
    for i in range(len(keys) - 1):          # a quote running over a page break
        if target in keys[i][-len(target):] + keys[i + 1][:len(target)]:
            return i + 1
    return None
