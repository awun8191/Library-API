from typing import Protocol, Tuple
from fastapi import UploadFile


class FileStorageRepository(Protocol):
    async def upload_file(self, file: UploadFile) -> Tuple[str, str]:
        """Upload file to storage and return (file_path, file_url)."""
        ...

    def read_file(self, file_path: str) -> bytes:
        """Read file content from storage."""
        ...

    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage."""
        ...