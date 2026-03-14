import re
from pathlib import Path


_FAX_ALLOWED_RE = re.compile(r"^[0-9+\-().\s]+$")


def is_valid_fax_number(value: str) -> bool:
    if not value:
        return False

    trimmed = value.strip()
    if not trimmed:
        return False

    if not _FAX_ALLOWED_RE.match(trimmed):
        return False

    digits = [ch for ch in trimmed if ch.isdigit()]
    return len(digits) >= 6


def is_pdf_file(path: str) -> bool:
    if not path:
        return False

    file_path = Path(path)
    if not file_path.is_file():
        return False

    if file_path.suffix.lower() != ".pdf":
        return False

    try:
        with file_path.open("rb") as handle:
            header = handle.read(4)
        return header == b"%PDF"
    except OSError:
        return False
