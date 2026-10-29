"""Text extraction from the files students send: .txt, .md, .pdf and .docx."""
from __future__ import annotations

import io

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 30_000
SUPPORTED = (".txt", ".md", ".pdf", ".docx")


class UnsupportedFile(Exception):
    pass


def extract_text(name: str, data: bytes) -> tuple[str, bool]:
    """Returns (text, was_truncated). Raises UnsupportedFile with a message fit for the user."""
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in (".txt", ".md"):
        text = data.decode("utf-8", errors="replace")
    elif ext == ".pdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as e:
            raise UnsupportedFile("Не удалось прочитать PDF. Возможно, он защищён паролем или повреждён.") from e
        if not text.strip():
            raise UnsupportedFile("В этом PDF нет текстового слоя (похоже, это скан). Пришлите PDF с текстом или текстовый файл.")
    elif ext == ".docx":
        from docx import Document
        try:
            doc = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            raise UnsupportedFile("Не удалось прочитать файл Word. Проверьте, что это .docx.") from e
    else:
        raise UnsupportedFile("Я читаю файлы .txt, .md, .pdf и .docx. Пришлите один из этих форматов.")
    text = text.strip()
    if not text:
        raise UnsupportedFile("Файл пустой.")
    return (text[:MAX_TEXT_CHARS], True) if len(text) > MAX_TEXT_CHARS else (text, False)
