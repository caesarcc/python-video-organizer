# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

video-organizer is a Python CLI that scans a video library (recursively, from a folder set in
`config.yaml`) and cleans it up in two passes:

1. **Duplicate detection** — groups videos that are byte-identical (SHA-256) or *probably* the
   same clip (similar duration + perceptual hash of a sampled frame, via ffmpeg/ffprobe), moves
   each group into a review folder, and renames the copies based on the filename judged most
   descriptive (longest stem).
2. **Short-video detection** — among whatever videos are left, finds anything under a configured
   duration and moves it into a separate review folder.

Every move is presented as a table and requires interactive confirmation before anything touches
disk (unless `--yes` or `--dry-run` is passed). Files are always **moved**, never copied.

## Commands

Setup:
```
pip install -e ".[dev]"
```

Copy the example config before first run — `config.yaml` is gitignored because it contains a real
local path:
```
cp config.example.yaml config.yaml   # then edit source_folder
```

Run:
```
python -m video_organizer.cli --config config.yaml
python -m video_organizer.cli --config config.yaml --dry-run   # show planned moves only
python -m video_organizer.cli --config config.yaml --yes       # skip confirmation prompts
```

Tests:
```
pytest
pytest tests/test_duplicates.py -k exact_hash   # single test
```

Requires `ffmpeg`/`ffprobe` on PATH for metadata extraction and perceptual hashing — without it,
duplicate detection falls back to exact-hash matches only (see `metadata.FFProbeNotFoundError`),
and short-video detection can't run at all since it needs duration.

## Architecture

Pipeline, driven end-to-end from `video_organizer/cli.py:main`:

```
scanner.find_videos()  ->  duplicates.find_duplicate_groups()  ->  mover (show/confirm/execute)
                       ->  short_videos.find_short_videos()    ->  mover (show/confirm/execute)
```

- `config.py` — loads and validates `config.yaml` into a `Config` dataclass. All tunables (source
  folder, review-folder names, hash distance threshold, duration tolerance, short-video threshold)
  live here; add new knobs here first.
- `scanner.py` — recursive file discovery; always excludes the configured review-folder names so
  re-runs don't re-scan already-sorted output.
- `metadata.py` — wraps `ffprobe` (JSON output) to get duration/resolution; this is the single
  point where ffmpeg absence is detected and surfaced (`FFProbeNotFoundError`).
- `hashing.py` — `sha256_file` for exact-duplicate matching; `perceptual_hash` extracts one frame
  via `ffmpeg` at the midpoint of the clip and hashes it with `imagehash.phash` for near-duplicate
  matching.
- `duplicates.py` — two-pass grouping: exact SHA-256 matches first, then a duration-tolerance +
  perceptual-hash-distance clustering pass over whatever wasn't already claimed by pass one.
  `pick_reference_name` chooses the longest filename stem in a group as the basis for renaming
  (used as the heuristic for "the file with more information in the title").
- `short_videos.py` — filters the (non-duplicate) remaining videos by
  `duration_seconds < max_duration_seconds`.
- `mover.py` — the only module that touches the filesystem for moves. `MovePlan` is a pure data
  object; `show_plan`/`confirm` are the human-in-the-loop gate; `execute_moves` uses `shutil.move`
  (works across drives) and `unique_destination` avoids clobbering existing files in the review
  folder.

Key invariant: nothing in `duplicates.py` or `short_videos.py` ever moves a file directly — they
only return data (`DuplicateGroup`, `Path` lists). `cli.py` turns that into `MovePlan`s, and
`mover.py` is the sole place `shutil.move` is called. Keep new detection rules following that same
"detect -> plan -> confirm -> execute" separation.
