"""Command-line entry point for video-organizer.

Pipeline:
    scanner.find_videos()
        -> duplicates.find_duplicate_groups()  -> show/confirm -> mover.execute_moves()
        -> short_videos.find_short_videos()     -> show/confirm -> mover.execute_moves()
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config, ConfigError, load_config
from .duplicates import DuplicateGroup, find_duplicate_groups, pick_reference_name
from .metadata import FFProbeNotFoundError
from .mover import MovePlan, confirm, execute_moves, show_plan, unique_destination
from .scanner import find_videos
from .short_videos import find_short_videos


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan a video library for duplicates and short clips.")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="Path to config.yaml")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--dry-run", action="store_true", help="Show planned moves without moving anything")
    return parser.parse_args(argv)


def build_duplicate_plans(config: Config, groups: list[DuplicateGroup]) -> list[MovePlan]:
    plans: list[MovePlan] = []
    review_root = config.duplicates_review_path
    for i, group in enumerate(groups, start=1):
        base_name = pick_reference_name(group)
        group_dir = review_root / f"{i:03d}_{base_name}"[:150]
        for j, video in enumerate(group.videos, start=1):
            dest_name = f"{base_name}_{j}{video.path.suffix}"
            destination = unique_destination(group_dir / dest_name)
            plans.append(MovePlan(source=video.path, destination=destination, reason=group.reason))
    return plans


def build_short_video_plans(config: Config, paths: list[Path]) -> list[MovePlan]:
    review_root = config.short_videos_review_path
    plans = []
    for p in paths:
        destination = unique_destination(review_root / p.name)
        plans.append(MovePlan(source=p, destination=destination, reason="shorter than configured minimum"))
    return plans


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    skip_dirs = {config.duplicates.review_folder_name, config.short_videos.review_folder_name}
    videos = find_videos(config.source_folder, config.video_extensions, skip_dirs=skip_dirs)
    print(f"Found {len(videos)} video file(s) under {config.source_folder}")

    moved_in_step_one: set[Path] = set()

    if config.duplicates.enabled:
        try:
            groups = find_duplicate_groups(videos, config.duplicates)
        except FFProbeNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        if groups:
            plans = build_duplicate_plans(config, groups)
            show_plan(plans, f"Step 1: {len(groups)} duplicate group(s) found")
            if args.dry_run:
                print("(dry run) Skipping move.")
            elif confirm("Move these files into the duplicates review folder?", assume_yes=args.yes):
                execute_moves(plans)
                moved_in_step_one.update(p.source for p in plans)
            else:
                print("Skipped.")
        else:
            print("Step 1: no duplicates found.")

    if config.short_videos.enabled:
        remaining = [v for v in videos if v not in moved_in_step_one]
        short_paths = find_short_videos(remaining, config.short_videos)
        if short_paths:
            plans = build_short_video_plans(config, short_paths)
            show_plan(
                plans,
                f"Step 2: {len(short_paths)} video(s) shorter than {config.short_videos.max_duration_seconds}s",
            )
            if args.dry_run:
                print("(dry run) Skipping move.")
            elif confirm("Move these files into the short-videos folder?", assume_yes=args.yes):
                execute_moves(plans)
            else:
                print("Skipped.")
        else:
            print("Step 2: no short videos found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
