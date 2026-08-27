#!/usr/bin/env python3
"""Build the deployable room schedule from Schedule Pro CSV data."""

from __future__ import annotations

import argparse
from pathlib import Path

from room_data import build_schedule_dataset, save_schedule_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="classes", help="Directory containing NJIT CSV files")
    parser.add_argument(
        "--output",
        default="data/schedule_data.json",
        help="Generated JSON artifact path",
    )
    parser.add_argument("--term", help="Optional six-digit NJIT term code")
    args = parser.parse_args()

    dataset = build_schedule_dataset(args.source, args.term)
    save_schedule_dataset(dataset, args.output)
    metadata = dataset["metadata"]
    output = Path(args.output)
    print(
        f"Built {metadata['term_name']} room data: "
        f"{len(dataset['room_list'])} rooms in {len(dataset['buildings'])} buildings"
    )
    print(f"Wrote {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
