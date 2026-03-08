#!/usr/bin/env python3
"""Download Open Images V7 images filtered by class into data/corpus/open-images/.

Uses the `fiftyone` library to download specific classes (Person, Dog, Cat, etc.)
from the Open Images V7 dataset.

Usage:
    uv run python scripts/download_corpus_openimages.py [--limit N] [--dry-run]
    uv run python scripts/download_corpus_openimages.py --classes Person Dog Cat
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = PROJECT_ROOT / "data" / "corpus" / "open-images"

DEFAULT_CLASSES = ["Person", "Dog", "Cat", "Animal"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Open Images V7 filtered by class")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max images to download per class (0 = all available)",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        default=DEFAULT_CLASSES,
        help=f"Open Images classes to download (default: {DEFAULT_CLASSES})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    parser.add_argument(
        "--split",
        default="train",
        choices=["train", "validation", "test"],
        help="Dataset split to download (default: train)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.dry_run:
        print("=== DRY RUN: Open Images V7 ===")
        print(f"  Target dir:  {CORPUS_DIR}")
        print(f"  Classes:     {args.classes}")
        print(f"  Split:       {args.split}")
        print(f"  Limit/class: {'all' if args.limit == 0 else args.limit}")
        print("  Approx images per class (train split):")
        print("    Person: ~600K  |  Dog: ~25K  |  Cat: ~18K  |  Animal: ~30K")
        print("  Source:      Open Images V7 via fiftyone")
        return

    try:
        import fiftyone as fo
        import fiftyone.zoo as foz
    except ImportError:
        print("ERROR: 'fiftyone' package not installed.", file=sys.stderr)
        print("  Install with: uv add fiftyone", file=sys.stderr)
        sys.exit(1)

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Downloading Open Images V7 ===")
    print(f"  Target dir:  {CORPUS_DIR}")
    print(f"  Classes:     {args.classes}")
    print(f"  Split:       {args.split}")
    print(f"  Limit/class: {'all' if args.limit == 0 else args.limit}")
    print()

    # fiftyone downloads into its own cache, then we copy to corpus dir
    load_kwargs: dict = {
        "label_types": ["detections"],
        "classes": args.classes,
        "split": args.split,
    }
    if args.limit > 0:
        load_kwargs["max_samples"] = args.limit * len(args.classes)

    print("Downloading via fiftyone (this may take a while on first run)...")
    dataset = foz.load_zoo_dataset(
        "open-images-v7",
        **load_kwargs,
    )

    # Copy images to corpus dir
    print()
    print("Copying images to corpus directory...")
    copied = 0
    skipped = 0

    for sample in dataset:
        src = Path(sample.filepath)
        if not src.exists():
            continue

        dst = CORPUS_DIR / src.name
        if dst.exists():
            skipped += 1
            continue

        shutil.copy2(src, dst)
        copied += 1

        if copied % 5000 == 0:
            print(f"  Progress: {copied:,} copied, {skipped:,} skipped")

    print()
    print("=== Open Images Download Complete ===")
    print(f"  Copied:  {copied:,}")
    print(f"  Skipped: {skipped:,} (already existed)")
    print(f"  Dir:     {CORPUS_DIR}")
    print()
    print("Note: fiftyone caches data in ~/fiftyone/. You can delete it to reclaim space.")

    # Cleanup fiftyone dataset registration (not the files)
    fo.delete_dataset(dataset.name)


if __name__ == "__main__":
    main()
