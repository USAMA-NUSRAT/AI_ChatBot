"""Read uploaded files and split their text into chunks."""

import io
import re

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".md")


class DocumentError(Exception):
    pass


def extract_text(filename: str, data: bytes) -> str:
    """Turn the raw bytes of an uploaded file into plain text."""
    name = filename.lower()

    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages)
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace")
    else:
        raise DocumentError(f"Unsupported file type. Allowed: {', '.join(SUPPORTED_EXTENSIONS)}")

    # Remove invisible control characters (e.g. PDF bullets often come out as \x7f),
    # keeping newlines and tabs
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text)

    if not text.strip():
        # Usually a scanned PDF: the pages are images, so there is no text to read
        raise DocumentError("No text found in the file. Scanned PDFs are not supported.")
    return text


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into chunks of at most `chunk_size` characters.

    Paragraphs are kept together when possible, and each chunk starts with the
    last `overlap` characters of the previous one so that a sentence cut at a
    boundary still appears whole in at least one chunk.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    # Break paragraphs that are too long on their own, at a space
    pieces = []
    for para in paragraphs:
        while len(para) > chunk_size:
            cut = para.rfind(" ", 0, chunk_size)
            if cut <= 0:
                cut = chunk_size
            pieces.append(para[:cut].strip())
            para = para[cut:].strip()
        if para:
            pieces.append(para)

    # Pack pieces into chunks
    chunks = []
    current = ""
    for piece in pieces:
        if current and len(current) + 2 + len(piece) > chunk_size:
            chunks.append(current)
            current = _tail(current, overlap)
            if len(current) + 2 + len(piece) > chunk_size:
                current = ""  # no room for overlap without going over the limit
        current = f"{current}\n\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


def _tail(text: str, size: int) -> str:
    """Last `size` characters of text, starting at a word boundary."""
    if size <= 0 or len(text) <= size:
        return ""
    tail = text[-size:]
    space = tail.find(" ")
    return tail[space + 1:] if space != -1 else tail
