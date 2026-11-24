"""Reading .docx files and splitting document text into chunks."""
from django.conf import settings
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_docx_text(file_obj) -> str:
    """Extract paragraphs and table cells from a .docx file (path or file-like)."""
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    doc = DocxDocument(file_obj)
    parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    return "\n\n".join(parts)


def split_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "؟ ", "! ", "؛ ", " ", ""],
    )
    return [c.strip() for c in splitter.split_text(text) if c.strip()]
