import base64
from dataclasses import dataclass
from pathlib import Path


OUTPUT_SUBDIRS = (
    "chapters_clean",
    "chapters_with_notes",
    "short_stories",
    "short_stories_with_notes",
)


@dataclass(frozen=True)
class ManagedFile:
    id: str
    name: str
    relative_path: str
    size: int
    modified_time: float


def encode_file_id(relative_path: str) -> str:
    raw = relative_path.replace("\\", "/").encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_file_id(file_id: str) -> str:
    padding = "=" * (-len(file_id) % 4)
    return base64.urlsafe_b64decode((file_id + padding).encode("ascii")).decode("utf-8")


def list_output_files(agent_root: Path) -> list[ManagedFile]:
    output_root = agent_root / "output"
    files: list[ManagedFile] = []
    for subdir in OUTPUT_SUBDIRS:
        folder = output_root / subdir
        if not folder.exists():
            continue
        for path in folder.glob("*.txt"):
            rel = path.relative_to(output_root).as_posix()
            stat = path.stat()
            files.append(
                ManagedFile(
                    id=encode_file_id(rel),
                    name=path.name,
                    relative_path=rel,
                    size=stat.st_size,
                    modified_time=stat.st_mtime,
                )
            )

    return sorted(files, key=lambda item: item.modified_time, reverse=True)


def get_output_file(agent_root: Path, file_id: str) -> tuple[ManagedFile, str]:
    output_root = (agent_root / "output").resolve()
    relative_path = decode_file_id(file_id)
    path = (output_root / relative_path).resolve()

    try:
        path.relative_to(output_root)
    except ValueError as exc:
        raise FileNotFoundError("非法文件路径。") from exc
    if not path.exists() or path.suffix.lower() != ".txt":
        raise FileNotFoundError("文件不存在。")

    stat = path.stat()
    rel = path.relative_to(output_root).as_posix()
    managed_file = ManagedFile(
        id=encode_file_id(rel),
        name=path.name,
        relative_path=rel,
        size=stat.st_size,
        modified_time=stat.st_mtime,
    )
    return managed_file, path.read_text(encoding="utf-8")


def latest_output_file(agent_root: Path) -> dict | None:
    files = list_output_files(agent_root)
    if not files:
        return None

    item, content = get_output_file(agent_root, files[0].id)
    return {
        "id": item.id,
        "name": item.name,
        "relative_path": item.relative_path,
        "size": item.size,
        "preview": content[:2000],
    }
