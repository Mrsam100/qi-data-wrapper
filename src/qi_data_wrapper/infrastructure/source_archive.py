import hashlib
import shutil
from pathlib import Path
from uuid import UUID


class SourceArchive:
    """Stores an immutable copy of a user-supplied source file for provenance."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def archive(self, dataset_id: UUID, source_file: Path) -> tuple[str, str]:
        if not source_file.is_file():
            raise FileNotFoundError(f"source file does not exist: {source_file}")
        relative_path = Path("raw") / "user_imports" / f"{dataset_id}{source_file.suffix.lower()}"
        destination = self._root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_file, destination)
        checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
        return relative_path.as_posix(), checksum
