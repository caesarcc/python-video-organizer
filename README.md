# video-organizer

Scans a video library (recursively, from a folder set in `config.yaml`) and helps clean it up in
two passes:

1. **Duplicate detection** — groups videos that are byte-identical or *probably* the same clip
   (similar duration + a matching sampled frame), moves each group into a review folder, and
   renames the copies based on whichever filename looks most descriptive.
2. **Short-video detection** — among whatever is left, finds anything under a configured duration
   and moves it into a separate review folder.

Every move is shown as a table and requires interactive confirmation before anything touches disk
(unless `--yes` or `--dry-run` is passed). Files are always **moved**, never copied.

## Requirements

- Python 3.10+
- `ffmpeg` / `ffprobe` on PATH — used to read duration/resolution and to sample a frame for
  near-duplicate matching. Without it, duplicate detection falls back to exact byte-hash matches
  only, and short-video detection can't run.

## Setup

```
pip install -e ".[dev]"
cp config.example.yaml config.yaml
```

Edit `config.yaml` — at minimum set `source_folder`. Everything else (review folder names, the
duplicate-similarity thresholds, the short-video cutoff) has a sensible default and can be tuned
later; see the comments in `config.example.yaml`.

## Usage

```
python -m video_organizer.cli --config config.yaml
python -m video_organizer.cli --config config.yaml --dry-run   # show planned moves only
python -m video_organizer.cli --config config.yaml --yes       # skip confirmation prompts
```

Or, after `pip install -e .`, the `video-organizer` console script is also available.

## Tests

```
pytest
```
