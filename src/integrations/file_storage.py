from pathlib import Path
from typing import Tuple
import uuid

from fastapi import UploadFile

from core.exceptions import FileUploadException
from core.repository import FileStorageRepository


class FileStorage(FileStorageRepository):
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or (Path(__file__).resolve().parents[2] / "Storage")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, file: UploadFile) -> Tuple[str, str]:
        if file.content_type != "application/pdf" and not (file.filename and file.filename.lower().endswith(".pdf")):
            raise FileUploadException("Only PDF files are allowed")

        file_name = f"{uuid.uuid4().hex}.pdf"
        target_path = self.base_dir / file_name

        try:
            content = await file.read()
            target_path.write_bytes(content)
        except OSError as exc:
            raise FileUploadException(f"Failed to store file: {exc}") from exc

        return str(target_path), f"/static/books/{file_name}"

    def read_file(self, file_path: str) -> bytes:
        path = Path(file_path)
        if not path.is_file():
            raise FileUploadException("File not found in storage", status_code=404)
        return path.read_bytes()

    def delete_file(self, file_path: str) -> bool:
        path = Path(file_path)
        if path.is_file():
            path.unlink()
            return True
        return False

