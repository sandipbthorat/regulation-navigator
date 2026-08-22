"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _discover_project_root() -> Path:
    configured = os.getenv("REGNAV_PROJECT_ROOT", "").strip()
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path.cwd(),
        Path(__file__).resolve().parents[2],
    ]
    for candidate in candidates:
        if candidate and (candidate / "data" / "corpus" / "starter_corpus.jsonl").exists():
            return candidate.resolve()
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = _discover_project_root()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    starter_corpus: Path = PROJECT_ROOT / "data" / "corpus" / "starter_corpus.jsonl"
    additional_corpus: Path | None = None
    chroma_dir: Path = PROJECT_ROOT / ".cache" / "chroma"
    top_k: int = 8
    use_llm: bool = False
    model: str = "gpt-5-mini"

    @classmethod
    def from_env(cls) -> Settings:
        extra = os.getenv("REGNAV_CORPUS_PATH", "").strip()
        chroma = os.getenv("REGNAV_CHROMA_DIR", ".cache/chroma").strip()
        chroma_path = Path(chroma)
        if not chroma_path.is_absolute():
            chroma_path = PROJECT_ROOT / chroma_path
        return cls(
            additional_corpus=Path(extra).expanduser().resolve() if extra else None,
            chroma_dir=chroma_path,
            top_k=max(3, min(20, int(os.getenv("REGNAV_TOP_K", "8")))),
            use_llm=_as_bool(os.getenv("REGNAV_USE_LLM")),
            model=os.getenv("REGNAV_MODEL", "gpt-5-mini").strip() or "gpt-5-mini",
        )
