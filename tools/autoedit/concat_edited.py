#!/usr/bin/env python3
"""Stitch already-edited clips (autoedit.py output) into one draft reel.

For previewing "everything shot/edited so far" as a single rough cut while
the rest of a large raw-footage batch is still being processed or fixed.
Straight cuts in filename order - no transitions, no re-ordering, no
trimming. Clips produced by autoedit.py's --vertical batch mode already
share codec/resolution/frame rate, so this "just works" as a quick draft.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}

# See tools/autoedit/autoedit.py for why this is needed on Japanese Windows:
# ffmpeg writes UTF-8 to stderr regardless of platform, but the default
# locale encoding there (cp932) can't decode all of it.
SUBPROCESS_TEXT_KWARGS = {"encoding": "utf-8", "errors": "replace"}


def run_ffmpeg(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_TEXT_KWARGS)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, required=True,
                    help="Directory containing already-edited clips (e.g. autoedit.py's --out folder)")
    p.add_argument("--pattern", default="*_edited.mp4",
                    help="Glob pattern for clips to include, relative to --input-dir (default: *_edited.mp4)")
    p.add_argument("--limit", type=int, default=None,
                    help="Only include the first N matching clips (in filename order) - "
                         "useful for a quick short preview instead of the full batch")
    p.add_argument("--out", type=Path, required=True, help="Output combined video path")
    p.add_argument("--copy", action="store_true",
                    help="Stream-copy instead of re-encoding (faster, but only safe if every "
                         "clip has identical codec/resolution/frame rate - fine for a batch that "
                         "all came from the same autoedit.py --vertical run)")
    args = p.parse_args()

    clips = sorted(
        c for c in args.input_dir.glob(args.pattern)
        if c.is_file() and c.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not clips:
        print(f"error: no clips matching {args.pattern!r} found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)
    if args.limit:
        clips = clips[:args.limit]

    print(f"Concatenating {len(clips)} clip(s) in this order:", file=sys.stderr)
    for c in clips:
        print(f"  {c.name}", file=sys.stderr)

    temp_dir = Path(tempfile.mkdtemp(prefix="concat_edited_"))
    try:
        filelist_path = temp_dir / "filelist.txt"
        lines = []
        for c in clips:
            escaped = str(c.resolve()).replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
        filelist_path.write_text("\n".join(lines), encoding="utf-8")

        args.out.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(filelist_path)]
        if args.copy:
            cmd += ["-c", "copy"]
        else:
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-c:a", "aac", "-b:a", "128k"]
        cmd += [str(args.out.resolve())]

        run_ffmpeg(cmd)
        print(f"\nDone: {args.out}", file=sys.stderr)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
