"""
Structural parsing of SAP / protocol / guidance documents.

Chunking is by heading, not token count, so downstream passes reason over
whole semantic sections and citations resolve to real section numbers and
pages.

Robustness measures (driven by real-world CSR/SAP layouts):
  - Running headers/footers (report dates, "FINAL CSR", page numbers,
    sponsor/protocol banners) are detected by cross-page repetition and
    stripped before heading detection.
  - Heading detection is strict: dotted multi-level numbers ("9.4.1"),
    "Appendix X", or bare-integer numbers ONLY when the title is mostly
    uppercase (e.g. "9 STATISTICAL METHODS"). Dates and prose fragments
    are rejected.
  - Contents / "List of ..." pages are detected by candidate density (many
    heading-like lines on one page) and folded into a single section
    instead of exploding into spurious headings.
  - Tables are extracted as Markdown (PyMuPDF find_tables for PDF, native
    walk for DOCX) and kept with the section they appear in.

PDF:   PyMuPDF (fitz).
DOCX:  python-docx (paragraph styles for headings; block walk keeps tables
       in document order).
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .schemas import DocumentSection

# "9", "9.4", "9.4.1", "Section 9.4", "Appendix A"
_NUMBERED = re.compile(
    r"^(?:section\s+)?((?:\d+\.)+\d*|\d+|appendix\s+[a-z0-9]+)[\s.:)\-]+(.{3,150})$",
    re.IGNORECASE,
)
_TOC_LEADER = re.compile(r"\.{3,}\s*\d+\s*$|\s{2,}\d{1,4}\s*$")   # "... 42" or "   42"
_DATE = re.compile(
    r"(?i)\b(?:\d{1,2}\s+)?(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\s+\d{2,4}\b"
)
_MAX_HEADING_CHARS = 160
_TOC_DENSITY = 6          # >this many heading candidates on one page => contents/list page


def parse_document(path: str | Path) -> list[DocumentSection]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(path)
    if suffix in (".docx", ".doc"):
        return _parse_docx(path)
    raise ValueError(f"Unsupported document type: {suffix} (expected .pdf or .docx)")


# --------------------------------------------------------------------- #
# Heading / guard predicates
# --------------------------------------------------------------------- #

def _heading_level(number: str) -> int:
    if number.lower().startswith("appendix"):
        return 1
    return number.rstrip(".").count(".") + 1


def _is_date(text: str) -> bool:
    return bool(_DATE.search(text))


def _wordlike(title: str) -> bool:
    """A real heading title has actual words, not just digits/punctuation."""
    if sum(c.isalpha() for c in title) < 3:
        return False
    return title[:1].isalpha() or title[:1] in "\"'("


def _mostly_upper(title: str) -> bool:
    letters = [c for c in title if c.isalpha()]
    if len(letters) < 2:
        return False
    return sum(c.isupper() for c in letters) / len(letters) >= 0.7


def _looks_like_heading(line: str) -> tuple[str, str, int] | None:
    """Strict structural heading test (font-independent)."""
    line = line.strip()
    if not line or len(line) > _MAX_HEADING_CHARS:
        return None
    if _TOC_LEADER.search(line) or _is_date(line):
        return None
    m = _NUMBERED.match(line)
    if not m:
        return None
    number, title = m.group(1).strip(), m.group(2).strip()
    if not _wordlike(title) or _is_date(title):
        return None
    dotted = "." in number.rstrip(".") or number.lower().startswith("appendix")
    if not number.lower().startswith("appendix"):
        number = number.rstrip(".")
    if dotted:
        return number, title, _heading_level(number)
    # Bare integer: only trust it when the title reads like a heading (caps).
    if _mostly_upper(title):
        return number, title, _heading_level(number)
    return None


def _heading_candidate(text: str, size: float, bold: bool, body_size: float
                       ) -> tuple[str | None, str, int] | None:
    """Structural test first, then a font-based path for title-case headings."""
    structural = _looks_like_heading(text)
    if structural:
        return structural
    text = text.strip()
    font_heading = (
        size >= body_size * 1.15
        and bold
        and 0 < len(text) <= _MAX_HEADING_CHARS
        and not text.endswith((".", ",", ";"))
        and not _is_date(text)
        and not _TOC_LEADER.search(text)
    )
    if not font_heading:
        return None
    m = _NUMBERED.match(text)
    if m and _wordlike(m.group(2).strip()) and not _is_date(m.group(2)):
        number, title = m.group(1).strip(), m.group(2).strip()
        return number, title, _heading_level(number)
    if _wordlike(text):
        return None, text, 2
    return None


# --------------------------------------------------------------------- #
# Boilerplate (running header/footer) detection
# --------------------------------------------------------------------- #

def _norm(line: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", line.strip().lower())).strip()


def _boilerplate_lines(pages_lines: list[list[str]]) -> set[str]:
    """Short lines that repeat across many pages are headers/footers."""
    npages = len(pages_lines)
    seen: dict[str, set[int]] = defaultdict(set)
    for page_idx, lines in enumerate(pages_lines):
        for text in lines:
            norm = _norm(text)
            if 0 < len(norm) <= 80:
                seen[norm].add(page_idx)
    threshold = max(3, int(0.2 * npages))
    return {norm for norm, pages in seen.items() if len(pages) >= threshold}


# --------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------- #

def _parse_pdf(path: Path) -> list[DocumentSection]:
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    try:
        # Pass A: collect lines (with style) and tables per page.
        pages: list[dict] = []
        for page_idx in range(doc.page_count):
            page = doc[page_idx]
            table_rects, table_md = _pdf_tables(page, fitz)
            lines: list[tuple[str, float, bool]] = []
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                if any(r.intersects(fitz.Rect(block["bbox"])) for r in table_rects):
                    continue  # rendered separately as a table
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    text = "".join(s["text"] for s in spans).strip()
                    if not text:
                        continue
                    max_size = max((s["size"] for s in spans), default=10.0)
                    is_bold = any(s.get("flags", 0) & 16 for s in spans)
                    lines.append((text, max_size, is_bold))
            pages.append({"page": page_idx + 1, "lines": lines, "tables": table_md})

        body_size = _modal_font_size(pages)
        boilerplate = _boilerplate_lines([[t for t, _, _ in p["lines"]] for p in pages])

        # Pass B: build sections.
        sections: list[dict] = []
        current = _new_section("Front matter", None, 1, page=1)
        buf: list[str] = []

        for p in pages:
            kept = [(t, s, b) for (t, s, b) in p["lines"] if _norm(t) not in boilerplate]
            candidates = [
                _heading_candidate(t, s, b, body_size) for (t, s, b) in kept
            ]
            toc_page = sum(c is not None for c in candidates) > _TOC_DENSITY
            for (text, _size, _bold), cand in zip(kept, candidates):
                heading = None if toc_page else cand
                if heading:
                    _close(current, buf, sections, p["page"])
                    number, title, level = heading
                    current = _new_section(title, number, level, page=p["page"])
                    buf = []
                else:
                    buf.append(text)
            for md in p["tables"]:
                buf.append(md)

        _close(current, buf, sections, doc.page_count)
        return _finalize(sections)
    finally:
        doc.close()


def _pdf_tables(page, fitz):
    """Return (list[Rect], list[markdown]) for detected tables on the page."""
    try:
        found = page.find_tables()
    except Exception:  # noqa: BLE001 - table finder is best-effort
        return [], []
    rects, mds = [], []
    for table in found.tables:
        if (table.row_count or 0) < 2 or (table.col_count or 0) < 2:
            continue
        try:
            md = table.to_markdown()
        except Exception:  # noqa: BLE001
            continue
        if md and md.strip():
            rects.append(fitz.Rect(table.bbox))
            mds.append(md.strip())
    return rects, mds


def _modal_font_size(pages: list[dict]) -> float:
    from collections import Counter

    counts: Counter[float] = Counter()
    for p in pages[:15]:
        for text, size, _bold in p["lines"]:
            counts[round(size, 1)] += len(text)
    return counts.most_common(1)[0][0] if counts else 10.0


# --------------------------------------------------------------------- #
# DOCX
# --------------------------------------------------------------------- #

def _parse_docx(path: Path) -> list[DocumentSection]:
    import docx
    from docx.document import Document as _Doc
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(str(path))

    # Collect raw blocks first so we can run boilerplate detection.
    raw_blocks: list[tuple[str, str]] = []  # (kind, text) kind in {para, head:N, table}
    for block in _iter_block_items(document, _Doc, Paragraph, Table):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            style = (block.style.name or "").lower()
            if style.startswith("heading"):
                try:
                    level = int(style.replace("heading", "").strip() or 1)
                except ValueError:
                    level = 1
                raw_blocks.append((f"head:{level}", text))
            else:
                raw_blocks.append(("para", text))
        else:  # Table
            rows = [" | ".join(c.text.strip() for c in row.cells) for row in block.rows]
            raw_blocks.append(("table", "\n".join(rows)))

    boilerplate = _boilerplate_lines([[t for kind, t in raw_blocks if kind != "table"]])

    sections: list[dict] = []
    current = _new_section("Front matter", None, 1, page=None)
    buf: list[str] = []
    for kind, text in raw_blocks:
        if kind.startswith("head") and _norm(text) not in boilerplate:
            level = int(kind.split(":")[1])
            _close(current, buf, sections, None)
            numbered = _looks_like_heading(text)
            number, title = (numbered[0], numbered[1]) if numbered else (None, text)
            current = _new_section(title, number, level, page=None)
            buf = []
        elif kind == "table":
            buf.append(text)
        elif _norm(text) not in boilerplate:
            buf.append(text)

    _close(current, buf, sections, None)
    return _finalize(sections)


def _iter_block_items(parent, _Doc, Paragraph, Table):
    """Yield paragraphs and tables in document order."""
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P

    body = parent.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


# --------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------- #

def _new_section(title: str, number: str | None, level: int, page: int | None) -> dict:
    return {"title": title, "number": number, "level": level, "page_start": page}


def _close(current: dict, buf: list[str], out: list[dict], page_end: int | None) -> None:
    text = "\n".join(buf).strip()
    if text or current["number"]:
        out.append({**current, "text": text, "page_end": page_end})


def _finalize(raw: list[dict]) -> list[DocumentSection]:
    sections: list[DocumentSection] = []
    number_to_id: dict[str, str] = {}
    for i, s in enumerate(raw):
        sid = f"s_{i:04d}"
        parent_id = None
        if s["number"] and "." in s["number"]:
            parent_number = s["number"].rstrip(".").rsplit(".", 1)[0]
            parent_id = number_to_id.get(parent_number)
        if s["number"]:
            number_to_id[s["number"].rstrip(".")] = sid
        sections.append(
            DocumentSection(
                section_id=sid,
                number=s["number"],
                title=s["title"],
                level=s["level"],
                parent_id=parent_id,
                text=s["text"],
                page_start=s["page_start"],
                page_end=s["page_end"],
                char_count=len(s["text"]),
            )
        )
    return sections
