"""Dedicated prompt log store for LLM/VLM interactions.

Stores prompt, response, model parameters, and metrics in a JSONL file
separate from operational logs (REQ-LOG-004, REQ-LOG-007).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class PromptLogEntry(BaseModel):
    """A single LLM/VLM interaction record."""

    timestamp: str = Field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    model: str = ""
    prompt_type: str = ""  # "vlm_describe", "llm_dossier", etc.
    input_text: str = ""
    output_text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    temperature: float = 0.0
    max_tokens: int = 0
    status: str = "success"  # "success", "error", "timeout"
    error_message: str = ""
    request_id: str = ""


class PromptLogStore:
    """Append-only JSONL store for prompt analytics."""

    def __init__(self, log_path: str | None = None) -> None:
        self._path = Path(log_path or "data/prompt_log.jsonl")
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry: PromptLogEntry) -> None:
        """Append a prompt log entry to the JSONL file."""
        try:
            with open(self._path, "a") as f:
                f.write(entry.model_dump_json() + "\n")
        except OSError:
            logger.warning("prompt_log_write_failed", path=str(self._path))

    def read_recent(self, limit: int = 100) -> list[PromptLogEntry]:
        """Read the most recent N entries."""
        if not self._path.exists():
            return []

        entries: list[PromptLogEntry] = []
        with open(self._path) as f:
            lines = f.readlines()

        for line in lines[-limit:]:
            try:
                entries.append(PromptLogEntry(**json.loads(line)))
            except (json.JSONDecodeError, ValueError):
                continue

        return entries

    def count(self) -> int:
        """Count total entries in the log."""
        if not self._path.exists():
            return 0
        with open(self._path) as f:
            return sum(1 for _ in f)
