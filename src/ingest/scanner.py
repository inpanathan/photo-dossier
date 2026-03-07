"""Recursive corpus directory scanner.

Walks the corpus directory, yields image files matching supported formats,
and tracks which files have already been indexed for incremental updates.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import structlog

from src.utils.config import settings

logger = structlog.get_logger(__name__)


def scan_corpus(
    corpus_dir: str | Path | None = None,
    supported_formats: list[str] | None = None,
    already_indexed: set[str] | None = None,
) -> Iterator[Path]:
    """Recursively scan corpus directory for image files.

    Args:
        corpus_dir: Root directory to scan. Defaults to settings.corpus.corpus_dir.
        supported_formats: File extensions to include. Defaults to settings.
        already_indexed: Set of relative paths already in the index (for incremental).

    Yields:
        Path objects for each discovered image file.
    """
    root = Path(corpus_dir or settings.corpus.corpus_dir).resolve()
    formats = supported_formats or settings.corpus.supported_formats
    indexed = already_indexed or set()

    if not root.exists():
        logger.error("corpus_dir_not_found", path=str(root))
        return

    if not root.is_dir():
        logger.error("corpus_dir_not_directory", path=str(root))
        return

    suffix_set = {f".{fmt.lower().lstrip('.')}" for fmt in formats}
    total = 0
    skipped = 0

    logger.info("corpus_scan_started", path=str(root), formats=list(suffix_set))

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in suffix_set:
            continue

        rel_path = str(path.relative_to(root))

        if rel_path in indexed:
            skipped += 1
            continue

        total += 1
        yield path

    logger.info(
        "corpus_scan_completed",
        total_new=total,
        skipped_indexed=skipped,
    )
