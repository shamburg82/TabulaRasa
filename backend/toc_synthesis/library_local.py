"""
File-based archetype library provider.

Reads the proprietary mock-shell library from a directory on the Posit
mount. Each Word document contains MANY archetypes (shells), each
preceded by a "Display ID:" marker. Layout:

    <SHELL_LIBRARY_ROOT>/
        v2024.1/
            core_shells.docx           dozens of standard displays
            oncology_shells.docx       oncology-specific displays
            pk_shells.docx             PK displays (in development)
            conventions.md             optional layout rules
            manifest.json              optional metadata overrides
                                       keyed by display_id
        v2024.2/
            ...

DISPLAY ID FORMAT (anchor for splitting):
    "Display ID: T_DISPO_001"
    "Display ID: F_KM_OS"
    "Display ID:T_AE_SOC_PT_001"   (whitespace flexible)
    case-insensitive

The first letter of the display id is treated as an output-type hint
(T->table, L->listing, F->figure). The rest of the id is opaque; metadata
inference falls back to keyword scanning of the shell text.

TABLE OF CONTENTS HANDLING:
    Each document typically has a TOC listing the display IDs. We
    distinguish TOC entries from real shells by candidate density on a
    single page: if a page contains many Display ID hits in close
    succession (more than _TOC_DENSITY hits in one TOC-likely region),
    we treat that region as TOC and exclude it from archetype extraction.
    Real shells are separated by paragraphs, page breaks, and tables, so
    they don't cluster the way a TOC does.

PARSING:
    DOCX -> python-docx, walk paragraphs and tables in document order
    PDF  -> PyMuPDF, page-by-page text + tables

Parsing happens lazily per version on first read, cached in memory.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

from .schemas import (
    Archetype, OutputCategory, OutputType,
    RowGroup, StatisticSet,
)

logger = logging.getLogger(__name__)


# Anchor matches "Display ID:" / "Display ID :" / "DisplayID:" / case-insensitive,
# followed by an identifier with letters, digits, underscores, hyphens, dots.
_DISPLAY_ID_RE = re.compile(
    r"display\s*id\s*[:\-]\s*([A-Za-z][A-Za-z0-9_.\-]*)",
    re.IGNORECASE,
)

# Hint that a line is a TOC entry: trailing dots + page number ("....... 42"),
# or wide whitespace + trailing number, or a leader-tab page-number style.
# Real shell anchors don't carry these markers.
_TOC_LINE_HINT = re.compile(r"\.{3,}\s*\d+\s*$|\t+\d+\s*$|\s{4,}\d+\s*$")

# When several Display IDs cluster within a narrow window without TOC line
# markers, we treat that span as TOC as a defensive fallback.
_TOC_CLUSTER_THRESHOLD = 6
_TOC_CLUSTER_WINDOW = 30


# Output-type from the first letter of the display id (best-effort hint).
_TYPE_FROM_PREFIX: dict[str, OutputType] = {
    "T": OutputType.TABLE,
    "L": OutputType.LISTING,
    "F": OutputType.FIGURE,
    "G": OutputType.FIGURE,    # some libraries use G for graphs
}


_CATEGORY_HINTS: dict[str, OutputCategory] = {
    "disposition": OutputCategory.BASELINE,
    "dispo": OutputCategory.BASELINE,
    "demog": OutputCategory.BASELINE,
    "baseline": OutputCategory.BASELINE,
    "exposure": OutputCategory.SAFETY,
    "expos": OutputCategory.SAFETY,
    "ae": OutputCategory.SAFETY,
    "adverse": OutputCategory.SAFETY,
    "teae": OutputCategory.SAFETY,
    "sae": OutputCategory.SAFETY,
    "labs": OutputCategory.SAFETY,
    "lab": OutputCategory.SAFETY,
    "chem": OutputCategory.SAFETY,
    "hemat": OutputCategory.SAFETY,
    "vital": OutputCategory.SAFETY,
    "ecg": OutputCategory.SAFETY,
    "efficacy": OutputCategory.EFFICACY,
    "eff": OutputCategory.EFFICACY,
    "primary": OutputCategory.EFFICACY,
    "secondary": OutputCategory.EFFICACY,
    "response": OutputCategory.EFFICACY,
    "survival": OutputCategory.EFFICACY,
    "km": OutputCategory.EFFICACY,
    "pk": OutputCategory.EFFICACY,    # PK often grouped under efficacy; manifest can override
    "disclosure": OutputCategory.DISCLOSURE,
    "ctgov": OutputCategory.DISCLOSURE,
}


class LocalMountArchetypeLibrary:
    """Reads archetypes from a local directory tree. Pinned to one version."""

    def __init__(self, root: str | Path, version: str):
        self.root = Path(root)
        self.version = version
        self.version_dir = self.root / version
        if not self.version_dir.is_dir():
            raise FileNotFoundError(f"Shell library version not found: {self.version_dir}")

    def list_archetypes(self) -> list[Archetype]:
        return list(_load_version(self.version_dir).archetypes)

    def get_archetype(self, archetype_id: str) -> Optional[Archetype]:
        return _load_version(self.version_dir).by_id.get(archetype_id)

    def list_conventions(self) -> list[str]:
        return list(_load_version(self.version_dir).conventions)


# --------------------------------------------------------------------- #
# Cached version load
# --------------------------------------------------------------------- #

class _ParsedVersion:
    def __init__(self, archetypes: list[Archetype], conventions: list[str]):
        self.archetypes = archetypes
        self.by_id = {a.archetype_id: a for a in archetypes}
        self.conventions = conventions


@lru_cache(maxsize=32)
def _load_version(version_dir_str_or_path) -> _ParsedVersion:
    version_dir = Path(version_dir_str_or_path)
    manifest = _read_manifest(version_dir)
    conventions = _read_conventions(version_dir)

    all_archetypes: list[Archetype] = []
    seen_ids: dict[str, str] = {}  # display_id -> source filename for collision tracking

    for file in sorted(version_dir.iterdir()):
        if file.name in ("conventions.md", "manifest.json"):
            continue
        if file.suffix.lower() not in (".docx", ".pdf"):
            continue
        try:
            shells = _parse_library_document(file)
        except Exception as exc:  # noqa: BLE001 - library data, not user-facing
            logger.exception("Failed to parse library document %s: %s", file, exc)
            continue
        logger.info("Parsed %d shells from %s", len(shells), file.name)
        for shell in shells:
            override = manifest.get(shell["display_id"], {})
            archetype = _build_archetype(shell, override, source=file.name)
            if archetype.archetype_id in seen_ids:
                logger.warning(
                    "Duplicate Display ID '%s' in %s (also in %s); using first occurrence",
                    archetype.archetype_id, file.name, seen_ids[archetype.archetype_id],
                )
                continue
            seen_ids[archetype.archetype_id] = file.name
            all_archetypes.append(archetype)
    logger.info("Loaded %d archetypes total from %s", len(all_archetypes), version_dir)
    return _ParsedVersion(archetypes=all_archetypes, conventions=conventions)


# --------------------------------------------------------------------- #
# Library document parsers (DOCX + PDF)
# --------------------------------------------------------------------- #

def _parse_library_document(file: Path) -> list[dict]:
    """Return [{display_id, text, tables}, ...] for every shell in the file."""
    if file.suffix.lower() == ".docx":
        blocks = _docx_blocks(file)
    else:
        blocks = _pdf_blocks(file)

    # Locate all Display ID hits with their block indices and find TOC spans.
    # Also flag hits whose host line carries a TOC-style trailer
    # (".... pagenum"), which is the primary TOC signal.
    hits: list[tuple[int, str, bool]] = []   # (block_idx, display_id, is_toc_line)
    for i, block in enumerate(blocks):
        if block["kind"] == "table":
            continue
        # Match against the line containing the anchor, not the whole block.
        for line in block["text"].splitlines():
            m = _DISPLAY_ID_RE.search(line)
            if m:
                is_toc_line = bool(_TOC_LINE_HINT.search(line))
                hits.append((i, m.group(1), is_toc_line))
                break  # one hit per block

    if not hits:
        logger.warning("No Display ID anchors found in %s", file.name)
        return []

    toc_block_indices = _detect_toc_block_indices(hits)

    # Real shells: hits whose block index is NOT inside the TOC set.
    real_hits = [(idx, did) for idx, did, _ in hits if idx not in toc_block_indices]

    # Slice the document: each shell spans from its anchor up to the block
    # just before the next anchor (or EOF).
    shells: list[dict] = []
    for n, (idx, did) in enumerate(real_hits):
        end = real_hits[n + 1][0] if n + 1 < len(real_hits) else len(blocks)
        body_blocks = blocks[idx:end]
        text_parts: list[str] = []
        tables_md: list[str] = []
        for b in body_blocks:
            if b["kind"] == "table":
                tables_md.append(b["text"])
            else:
                text_parts.append(b["text"])
        shells.append({
            "display_id": did,
            "text": "\n".join(text_parts).strip(),
            "tables": tables_md,
        })
    return shells


def _detect_toc_block_indices(hits: list[tuple[int, str, bool]]) -> set[int]:
    """Return the set of block indices that are TOC entries.

    Two signals combine:

    Primary - TOC-line markers (".......pagenum" or wide whitespace + pagenum)
    on the line carrying the Display ID. This catches the standard Word /
    PDF table-of-contents formatting and removes the ambiguity between
    "last TOC entry" and "first real shell" when they sit adjacent.

    Backup - candidate clustering. If several hits cluster within a narrow
    window of blocks without TOC-line markers (TOC formatting was lost,
    perhaps after a copy/paste), we treat the dense run as TOC. The
    threshold is strict enough that legitimate adjacent shells aren't
    flagged.
    """
    toc: set[int] = set()

    # Primary signal: lines marked as TOC by their formatting.
    for idx, _did, is_toc_line in hits:
        if is_toc_line:
            toc.add(idx)

    # Backup: dense clustering among the REMAINING hits (those without TOC-line
    # markers). We don't want a real-shell run to ever be flagged, so the
    # threshold here is the strict cluster heuristic.
    remaining = [(idx, did) for idx, did, is_toc_line in hits if not is_toc_line]
    if remaining:
        idxs = [h[0] for h in remaining]
        n = len(idxs)
        i = 0
        while i < n:
            j = i
            while j + 1 < n and idxs[j + 1] - idxs[i] < _TOC_CLUSTER_WINDOW:
                j += 1
            if j - i + 1 > _TOC_CLUSTER_THRESHOLD:
                for k in range(i, j + 1):
                    toc.add(idxs[k])
                i = j + 1
            else:
                i += 1

    if toc:
        sample = sorted(toc)[:8]
        logger.info("Detected %d TOC-entry block indices (sample: %s)",
                    len(toc), sample)
    return toc


def _docx_blocks(file: Path) -> list[dict]:
    """Walk a .docx in document order, yielding paragraphs and tables."""
    import docx
    from docx.document import Document as _Doc
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P

    document = docx.Document(str(file))
    blocks: list[dict] = []
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            para = Paragraph(child, document)
            text = para.text.strip()
            if text:
                blocks.append({"kind": "para", "text": text})
        elif isinstance(child, CT_Tbl):
            table = Table(child, document)
            rows = [" | ".join(c.text.strip() for c in row.cells) for row in table.rows]
            blocks.append({"kind": "table", "text": "\n".join(rows)})
    return blocks


def _pdf_blocks(file: Path) -> list[dict]:
    """Walk a PDF page-by-page, yielding text blocks and table markdown."""
    import fitz  # PyMuPDF

    blocks: list[dict] = []
    doc = fitz.open(file)
    try:
        for page in doc:
            # Tables first (best-effort)
            table_rects = []
            try:
                found = page.find_tables()
                for t in found.tables:
                    if (t.row_count or 0) < 2 or (t.col_count or 0) < 2:
                        continue
                    try:
                        md = t.to_markdown()
                    except Exception:  # noqa: BLE001
                        continue
                    if md and md.strip():
                        table_rects.append(fitz.Rect(t.bbox))
                        blocks.append({"kind": "table", "text": md.strip()})
            except Exception:  # noqa: BLE001
                pass
            # Then text, skipping anything that fell inside a detected table
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                bbox = fitz.Rect(block["bbox"])
                if any(r.intersects(bbox) for r in table_rects):
                    continue
                lines = []
                for line in block.get("lines", []):
                    text = "".join(s["text"] for s in line.get("spans", [])).strip()
                    if text:
                        lines.append(text)
                if lines:
                    blocks.append({"kind": "para", "text": "\n".join(lines)})
    finally:
        doc.close()
    return blocks


# --------------------------------------------------------------------- #
# Archetype construction from a parsed shell
# --------------------------------------------------------------------- #

def _build_archetype(shell: dict, override: dict, *, source: str) -> Archetype:
    display_id = shell["display_id"]
    text = shell["text"]
    title = override.get("name") or _extract_title(text, display_id)
    output_type = (OutputType(override["output_type"]) if override.get("output_type")
                   else _infer_type_from_id(display_id))
    output_category = (OutputCategory(override["output_category"])
                       if override.get("output_category")
                       else _infer_category(display_id, text))
    keywords = override.get("keywords") or _extract_keywords(display_id, text)
    description = override.get("description") or _short_description(text, title)
    footnotes = override.get("standard_footnotes") or _extract_footnotes(text)

    return Archetype(
        archetype_id=override.get("archetype_id") or display_id,
        name=title,
        description=description,
        output_type=output_type,
        output_category=output_category,
        typical_population=override.get("typical_population"),
        keywords=keywords,
        row_groups=[RowGroup(**rg) for rg in override.get("row_groups", [])],
        statistic_sets=[StatisticSet(**ss) for ss in override.get("statistic_sets", [])],
        standard_footnotes=footnotes,
    )


def _infer_type_from_id(display_id: str) -> OutputType:
    prefix = display_id[:1].upper()
    return _TYPE_FROM_PREFIX.get(prefix, OutputType.TABLE)


def _infer_category(display_id: str, text: str) -> OutputCategory:
    haystack = (display_id + " " + text[:2000]).lower()
    # Score each category by how many of its hint tokens appear
    scores: Counter[OutputCategory] = Counter()
    for hint, cat in _CATEGORY_HINTS.items():
        if hint in haystack:
            scores[cat] += 1
    if scores:
        return scores.most_common(1)[0][0]
    return OutputCategory.SAFETY


def _extract_title(text: str, display_id: str) -> str:
    """First non-trivial line after the Display ID anchor."""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip the anchor line itself
        if _DISPLAY_ID_RE.search(line) and len(line) < 80:
            continue
        # Skip generic boilerplate lines
        if line.lower().startswith(("title:", "source:", "page", "footer", "header")):
            continue
        if 5 < len(line) < 200:
            return line
    return display_id


def _short_description(text: str, title: str) -> str:
    """First ~3 substantive lines of the shell, after the title."""
    interesting: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line == title:
            continue
        if _DISPLAY_ID_RE.search(line) and len(line) < 80:
            continue
        interesting.append(line)
        if len(interesting) >= 3 or sum(len(s) for s in interesting) > 400:
            break
    return " ".join(interesting)[:500] or title


_KEYWORD_STOP = {
    "the","of","and","in","to","a","for","with","by","on","from","is","are",
    "was","were","will","be","as","at","or","this","that","an","display","id",
    "table","listing","figure","study","subject","subjects","group","groups",
}


def _extract_keywords(display_id: str, text: str, limit: int = 20) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", (display_id + " " + text).lower())
    counts = Counter(w for w in words if w not in _KEYWORD_STOP)
    return [w for w, _ in counts.most_common(limit)]


_FOOTNOTE_PATTERNS = [
    re.compile(r"^(?:Note|Notes?|Footnote|Source)\s*[:\-]\s*(.+)$"),
    re.compile(r"^[\u00B9\u00B2\u00B3\u2070-\u2079\*\u2020\u2021]\s*(.+)$"),
    re.compile(r"^\[\d+\]\s*(.+)$"),
    re.compile(r"^\d+\s+(.+(?:treatment|baseline|safety|efficacy|MedDRA|LOCF|TEAE).+)$",
               re.IGNORECASE),
]


def _extract_footnotes(text: str) -> list[str]:
    found: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        for pat in _FOOTNOTE_PATTERNS:
            m = pat.match(line)
            if m:
                snippet = m.group(1).strip()
                if 10 <= len(snippet) <= 400:
                    found.append(snippet)
                break
    return found


# --------------------------------------------------------------------- #
# Manifest + conventions (unchanged contract)
# --------------------------------------------------------------------- #

def _read_manifest(version_dir: Path) -> dict[str, dict]:
    path = version_dir / "manifest.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning("Invalid manifest.json in %s: %s", version_dir, exc)
        return {}


def _read_conventions(version_dir: Path) -> list[str]:
    path = version_dir / "conventions.md"
    if not path.is_file():
        return []
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        stripped = re.sub(r"^[-*]\s+|^\d+\.\s+", "", stripped)
        lines.append(stripped)
    return lines
