#!/usr/bin/env python3
"""Download COCO 2017 train images into data/corpus/coco/.

Uses the HuggingFace `datasets` library to stream COCO images without
needing the full dataset in memory.

Usage:
    uv run python scripts/download_corpus_coco.py [--limit N] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = PROJECT_ROOT / "data" / "corpus" / "coco"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download COCO 2017 train images")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max images to download (0 = all, ~118K)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.dry_run:
        print("=== DRY RUN: COCO 2017 Train ===")
        print(f"  Target dir:  {CORPUS_DIR}")
        print(f"  Limit:       {'all (~118K)' if args.limit == 0 else args.limit}")
        print(f"  Est. size:   ~18 GB (full) / ~{args.limit * 150 // 1024} MB (limited)")
        print("  Source:      HuggingFace detection-datasets/coco")
        return

    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: 'datasets' package not installed.", file=sys.stderr)
        print("  Install with: uv add datasets Pillow", file=sys.stderr)
        sys.exit(1)

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    # Count existing files for resume support
    existing = set(p.name for p in CORPUS_DIR.glob("*.jpg"))
    if existing:
        print(f"Found {len(existing)} existing images — will skip them.")

    print("=== Downloading COCO 2017 Train ===")
    print(f"  Target dir:  {CORPUS_DIR}")
    print(f"  Limit:       {'all (~118K)' if args.limit == 0 else args.limit}")
    print()

    # Stream to avoid loading entire dataset in memory
    print("Loading dataset (streaming)...")
    ds = load_dataset(
        "detection-datasets/coco",
        split="train",
        streaming=True,
    )

    saved = 0
    skipped = 0
    errors = 0
    total_limit = args.limit if args.limit > 0 else float("inf")

    for i, row in enumerate(ds):
        if saved >= total_limit:
            break

        filename = f"{i:06d}.jpg"
        filepath = CORPUS_DIR / filename

        if filename in existing:
            skipped += 1
            continue

        try:
            image = row["image"]
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.save(filepath, "JPEG", quality=90)
            saved += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  WARNING: Failed to save image {i}: {e}", file=sys.stderr)
            continue

        if saved % 1000 == 0:
            total = saved + skipped
            print(f"  Progress: {saved:,} saved, {skipped:,} skipped ({total:,} processed)")

    print()
    print("=== COCO Download Complete ===")
    print(f"  Saved:   {saved:,}")
    print(f"  Skipped: {skipped:,} (already existed)")
    print(f"  Errors:  {errors:,}")
    print(f"  Dir:     {CORPUS_DIR}")


if __name__ == "__main__":
    main()
