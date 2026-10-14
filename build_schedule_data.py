#!/usr/bin/env python3
"""Build the deployable room schedule from Schedule Pro CSV data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from room_data import (
    ScheduleDataError,
    build_schedule_dataset,
    load_schedule_dataset,
    save_schedule_dataset,
)


def refresh_schedule(source: str | Path, output: str | Path, config: str | Path) -> dict:
    """Publish only the configured semester with sufficient campus coverage."""
    settings = json.loads(Path(config).read_text(encoding="utf-8"))
    term = settings["active_term"]
    dataset = build_schedule_dataset(source, term=term)
    minimum_rooms = settings["minimum_rooms"]
    minimum_buildings = settings["minimum_buildings"]
    if Path(output).exists():
        previous = load_schedule_dataset(output)
        if previous["metadata"]["term"] == term:
            minimum_rooms = max(minimum_rooms, len(previous["room_list"]) * 0.8)
            minimum_buildings = max(minimum_buildings, len(previous["buildings"]) * 0.8)
    rooms = len(dataset["room_list"])
    buildings = len(dataset["buildings"])
    if rooms < minimum_rooms or buildings < minimum_buildings:
        raise ScheduleDataError(
            f"Refusing incomplete term {term}: {rooms} rooms in {buildings} buildings; "
            f"need at least {minimum_rooms:g} rooms and {minimum_buildings:g} buildings. "
            "The existing dataset was not changed."
        )
    save_schedule_dataset(dataset, output)
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="classes", help="Directory containing NJIT CSV files")
    parser.add_argument(
        "--output",
        default="data/schedule_data.json",
        help="Generated JSON artifact path",
    )
    parser.add_argument("--term", help="Optional six-digit NJIT term code")
    parser.add_argument(
        "--refresh-config",
        help="Active semester and minimum coverage settings for guarded refreshes",
    )
    args = parser.parse_args()

    if args.refresh_config and args.term:
        parser.error("Use --refresh-config or --term, not both")
    if args.refresh_config:
        try:
            dataset = refresh_schedule(args.source, args.output, args.refresh_config)
        except ScheduleDataError as exc:
            parser.exit(1, f"Schedule refresh rejected: {exc}\n")
    else:
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
