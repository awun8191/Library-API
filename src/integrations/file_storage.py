from pathlib import Path
import uuid

from core.exceptions import FileNotFoundException, FileUploadException


class FileStorage:
    """Store uploads on the local disk.

    The database keeps only the file name. The full path is built from
    ``base_dir`` at read time, so the storage folder can move without
    breaking stored books.
    """

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = (base_dir or (Path(__file__).resolve().parents[2] / "Storage")).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, file_name: str) -> Path:
        """Return the path of a stored file, kept inside the storage folder."""
        # Path(...).name drops any directory part, which also covers rows
        # written before the switch to bare file names.
        path = (self.base_dir / Path(file_name).name).resolve()
        if path.parent != self.base_dir:
            raise FileNotFoundException()
        return path

    def store_file(self, content: bytes) -> str:
        file_name = f"{uuid.uuid4().hex}.pdf"
        try:
            (self.base_dir / file_name).write_bytes(content)
        except OSError as exc:
            raise FileUploadException("Failed to store the file") from exc
        return file_name

    def get_file_path(self, file_path: str) -> str:
        path = self._resolve(file_path)
        if not path.is_file():
            raise FileNotFoundException()
        return str(path)

    def delete_file(self, file_path: str) -> bool:
        try:
            path = self._resolve(file_path)
        except FileNotFoundException:
            return False
        if path.is_file():
            path.unlink()
            return True
        return False
