"""Document parser extracting text, hierarchy, tables, and sections from PDF, DOCX, and Markdown files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ExtractedSection(BaseModel):
    title: str
    content: str
    level: int = 1
    tables: List[List[List[str]]] = Field(default_factory=list)


class DocumentAnalysis(BaseModel):
    source_file: str
    file_type: str
    total_characters: int
    title: str
    summary: str
    sections: List[ExtractedSection] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    terminology: List[str] = Field(default_factory=list)


class DocumentIngestionEngine:
    """Ingests source documents and transforms them into structured presentation material."""

    @classmethod
    def ingest_file(cls, file_path: str | Path) -> DocumentAnalysis:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Source document not found: {path}")

        ext = path.suffix.lower()
        if ext == ".pdf":
            return cls._ingest_pdf(path)
        elif ext in (".docx", ".doc"):
            return cls._ingest_docx(path)
        elif ext in (".md", ".txt", ".rst"):
            return cls._ingest_markdown_or_text(path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .pdf, .docx, .md, .txt")

    @classmethod
    def _ingest_pdf(cls, path: Path) -> DocumentAnalysis:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        num_pages = len(reader.pages)
        full_text = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                full_text.append(f"--- Page {i+1} ---\n" + text.strip())

        combined = "\n\n".join(full_text)
        return cls._structure_raw_text(
            source_file=path.name,
            file_type="PDF",
            raw_text=combined,
            fallback_title=path.stem.replace("_", " ").title(),
        )

    @classmethod
    def _ingest_docx(cls, path: Path) -> DocumentAnalysis:
        import docx
        doc = docx.Document(str(path))
        sections: List[ExtractedSection] = []
        current_title = path.stem.replace("_", " ").title()
        current_paragraphs: List[str] = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if p.style.name.startswith("Heading"):
                if current_paragraphs:
                    sections.append(ExtractedSection(title=current_title, content="\n".join(current_paragraphs)))
                    current_paragraphs = []
                current_title = text
            else:
                current_paragraphs.append(text)

        if current_paragraphs:
            sections.append(ExtractedSection(title=current_title, content="\n".join(current_paragraphs)))

        # Also extract tables
        tables_data: List[List[List[str]]] = []
        for t in doc.tables:
            tbl_rows = []
            for row in t.rows:
                tbl_rows.append([cell.text.strip() for cell in row.cells])
            if tbl_rows:
                tables_data.append(tbl_rows)

        full_content = "\n\n".join([f"## {s.title}\n{s.content}" for s in sections])
        return DocumentAnalysis(
            source_file=path.name,
            file_type="DOCX",
            total_characters=len(full_content),
            title=path.stem.replace("_", " ").title(),
            summary=full_content[:500] + ("..." if len(full_content) > 500 else ""),
            sections=sections,
            key_findings=[s.title for s in sections[:6]],
            terminology=[],
        )

    @classmethod
    def _ingest_markdown_or_text(cls, path: Path) -> DocumentAnalysis:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        lines = content.split("\n")
        sections: List[ExtractedSection] = []
        current_title = path.stem.replace("_", " ").title()
        current_lines: List[str] = []

        for line in lines:
            if line.startswith("#"):
                if current_lines:
                    sections.append(ExtractedSection(title=current_title, content="\n".join(current_lines).strip()))
                    current_lines = []
                current_title = line.lstrip("#").strip()
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(ExtractedSection(title=current_title, content="\n".join(current_lines).strip()))

        return DocumentAnalysis(
            source_file=path.name,
            file_type="Markdown/Text",
            total_characters=len(content),
            title=path.stem.replace("_", " ").title(),
            summary=content[:500] + ("..." if len(content) > 500 else ""),
            sections=sections,
            key_findings=[s.title for s in sections[:6]],
            terminology=[],
        )

    @classmethod
    def _structure_raw_text(cls, source_file: str, file_type: str, raw_text: str, fallback_title: str) -> DocumentAnalysis:
        # Segment by headings or page breaks
        blocks = raw_text.split("--- Page ")
        sections: List[ExtractedSection] = []
        for block in blocks:
            b = block.strip()
            if not b:
                continue
            lines = b.split("\n")
            header = lines[0].strip() if len(lines) > 0 else "Overview"
            body = "\n".join(lines[1:]).strip() if len(lines) > 1 else b
            sections.append(ExtractedSection(title=f"Section: {header[:40]}", content=body[:2000]))

        return DocumentAnalysis(
            source_file=source_file,
            file_type=file_type,
            total_characters=len(raw_text),
            title=fallback_title,
            summary=raw_text[:600] + "...",
            sections=sections[:15],
            key_findings=[],
            terminology=[],
        )
