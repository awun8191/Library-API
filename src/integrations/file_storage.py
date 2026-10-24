import asyncio
from pathlib import Path
import uuid

from core.exceptions import FileNotFoundException, FileUploadException


class FileStorage:
    """Store uploads on the local disk."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or (Path(__file__).resolve().parents[2] / "Storage")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def store_file(self, content: bytes) -> str:
        file_name = f"{uuid.uuid4().hex}.pdf"
        target_path = self.base_dir / file_name

        try:
            await asyncio.to_thread(target_path.write_bytes, content)
        except OSError as exc:
            raise FileUploadException("Failed to store the file") from exc

        return str(target_path)

    def get_file_path(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundException()
        return str(path)

    def delete_file(self, file_path: str) -> bool:
        path = Path(file_path)
        if path.is_file():
            path.unlink()
            return True
        return False
