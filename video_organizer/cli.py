"""Ponto de entrada de linha de comando do video-organizer.

Pipeline:
    scanner.find_videos()
        -> duplicates.find_duplicate_groups()  -> exibe/confirma -> mover.execute_moves()
        -> short_videos.find_short_videos()     -> exibe/confirma -> mover.execute_moves()
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import Config, ConfigError, load_config
from .duplicates import DuplicateGroup, find_duplicate_groups, pick_reference_name
from .metadata import FFProbeNotFoundError, VideoMetadata
from .mover import MovePlan, confirm, console, execute_moves, show_plan, unique_destination, write_report
from .scanner import find_videos
from .short_videos import find_short_videos


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan a video library for duplicates and short clips.")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="Path to config.yaml")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--dry-run", action="store_true", help="Show planned moves without moving anything")
    return parser.parse_args(argv)


@dataclass
class DuplicateReport:
    group_dir: Path
    content: str


def build_duplicate_report(group: DuplicateGroup) -> str:
    lines = [f"Duplicate group - {group.reason}", ""]
    for video in group.videos:
        lines.append(f"Original location: {video.path.resolve()}")
        lines.append(
            f"  duration: {video.duration_seconds:.2f}s, "
            f"resolution: {video.width}x{video.height}, "
            f"size: {video.size_bytes} bytes"
        )
        lines.append("")
    return "\n".join(lines)


def build_duplicate_plans(config: Config, groups: list[DuplicateGroup]) -> tuple[list[MovePlan], list[DuplicateReport]]:
    plans: list[MovePlan] = []
    reports: list[DuplicateReport] = []
    review_root = config.duplicates_review_path
    reserved: set[Path] = set()
    for i, group in enumerate(groups, start=1):
        base_name = pick_reference_name(group)
        group_dir = review_root / f"{i:03d}_{base_name}"[:150]
        for video in group.videos:
            destination = unique_destination(group_dir / video.path.name, reserved)
            plans.append(MovePlan(source=video.path, destination=destination, reason=group.reason))
        reports.append(DuplicateReport(group_dir=group_dir, content=build_duplicate_report(group)))
    return plans, reports


def build_short_video_plans(config: Config, videos: list[VideoMetadata]) -> list[MovePlan]:
    review_root = config.short_videos_review_path
    plans = []
    reserved: set[Path] = set()
    for video in videos:
        destination = unique_destination(review_root / video.path.name, reserved)
        plans.append(MovePlan(source=video.path, destination=destination, reason="shorter than configured minimum"))
    return plans


def build_short_videos_report(videos: list[VideoMetadata]) -> str:
    buffer = io.StringIO()
    # lineterminator="\n": o csv.writer usa "\r\n" por padrão, e como o conteúdo é gravado em
    # disco depois via write_text (modo texto, que já traduz "\n" para o separador do sistema),
    # deixar o "\r\n" do csv passar por essa tradução de novo resultava em "\r\r\n" - uma linha
    # em branco extra a cada linha ao abrir no Excel/Notepad.
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["nome_arquivo", "caminho_completo_origem", "data_criacao_arquivo", "tempo_video", "tamanho_arquivo"])
    for video in videos:
        writer.writerow([
            video.path.name,
            str(video.path.resolve()),
            datetime.fromtimestamp(video.created_at).strftime("%Y-%m-%d %H:%M:%S"),
            f"{video.duration_seconds:.2f}",
            video.size_bytes,
        ])
    return buffer.getvalue()


def confirm_target(config: Config) -> bool:
    """Mostra a pasta que será varrida e quais etapas de detecção estão ativas, e pede uma
    confirmação explícita antes de começar. Roda sempre - inclusive com --yes ou --dry-run -
    porque source_folder pode ter sido inferido silenciosamente a partir da pasta atual."""
    if config.source_folder_from_default:
        console.print(
            f"Source folder: {config.source_folder} "
            "[dim](source_folder not set in config.yaml - using the current directory)[/dim]"
        )
    else:
        console.print(f"Source folder: {config.source_folder}")

    console.print(f"  duplicates:   {'enabled' if config.duplicates.enabled else 'disabled'}")
    console.print(f"  short_videos: {'enabled' if config.short_videos.enabled else 'disabled'}")

    return confirm("Proceed with this folder and these settings?")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    if not confirm_target(config):
        print("Aborted.")
        return 0

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
            plans, reports = build_duplicate_plans(config, groups)
            show_plan(plans, f"Step 1: {len(groups)} duplicate group(s) found")
            if args.dry_run:
                print("(dry run) Skipping move.")
            elif confirm("Move these files into the duplicates review folder?", assume_yes=args.yes):
                execute_moves(plans)
                for report in reports:
                    write_report(report.group_dir / "duplicate_report.txt", report.content)
                moved_in_step_one.update(p.source for p in plans)
            else:
                print("Skipped.")
        else:
            print("Step 1: no duplicates found.")

    if config.short_videos.enabled:
        remaining = [v for v in videos if v not in moved_in_step_one]
        short_videos = find_short_videos(remaining, config.short_videos)
        if short_videos:
            plans = build_short_video_plans(config, short_videos)
            show_plan(
                plans,
                f"Step 2: {len(short_videos)} video(s) shorter than {config.short_videos.max_duration_seconds}s",
            )
            if args.dry_run:
                print("(dry run) Skipping move.")
            elif confirm("Move these files into the short-videos folder?", assume_yes=args.yes):
                execute_moves(plans)
                write_report(
                    config.short_videos_review_path / "short_videos_report.csv",
                    build_short_videos_report(short_videos),
                )
            else:
                print("Skipped.")
        else:
            print("Step 2: no short videos found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
