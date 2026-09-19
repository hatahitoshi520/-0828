#!/usr/bin/env python3
"""Stitch already-edited clips (autoedit.py output) into one draft reel.

For previewing "everything shot/edited so far" as a single rough cut while
the rest of a large raw-footage batch is still being processed or fixed.
Straight cuts in filename order - no transitions, no re-ordering, no
trimming. Clips produced by autoedit.py's --vertical batch mode already
share codec/resolution/frame rate, so this "just works" as a quick draft.
"""
import argparse
import json
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


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True, **SUBPROCESS_TEXT_KWARGS,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def select_for_target_duration(clips, target):
    """Walk clips in order, taking each whole until the budget runs low,
    then trimming the last one so the total lands on `target`."""
    selected = []
    total = 0.0
    for c in clips:
        if total >= target - 0.05:
            break
        full_dur = probe_duration(c)
        use_dur = min(full_dur, target - total)
        if use_dur <= 0.05:
            break
        selected.append((c, use_dur))
        total += use_dur
    return selected, total


def build_trimmed_concat_cmd(selected, out_path):
    inputs = []
    filter_parts = []
    v_labels, a_labels = [], []
    for i, (path, dur) in enumerate(selected):
        inputs += ["-i", str(path.resolve())]
        filter_parts.append(f"[{i}:v]trim=start=0:end={dur},setpts=PTS-STARTPTS[v{i}]")
        filter_parts.append(f"[{i}:a]atrim=start=0:end={dur},asetpts=PTS-STARTPTS[a{i}]")
        v_labels.append(f"[v{i}]")
        a_labels.append(f"[a{i}]")

    concat_inputs = "".join(f"{v}{a}" for v, a in zip(v_labels, a_labels))
    filter_parts.append(f"{concat_inputs}concat=n={len(selected)}:v=1:a=1[outv][outa]")
    filter_complex = ";".join(filter_parts)

    return [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", str(out_path.resolve()),
    ]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, required=True,
                    help="Directory containing already-edited clips (e.g. autoedit.py's --out folder)")
    p.add_argument("--pattern", default="*_edited.mp4",
                    help="Glob pattern for clips to include, relative to --input-dir (default: *_edited.mp4)")
    p.add_argument("--limit", type=int, default=None,
                    help="Only consider the first N matching clips (in filename order) - "
                         "useful for a quick short preview instead of the full batch")
    p.add_argument("--target-duration", type=float, default=None,
                    help="Trim the result to about this many seconds, in filename order: "
                         "clips are included whole until the budget runs low, then the last "
                         "one is trimmed to land on the target. Incompatible with --copy "
                         "(trimming requires re-encoding).")
    p.add_argument("--out", type=Path, required=True, help="Output combined video path")
    p.add_argument("--copy", action="store_true",
                    help="Stream-copy instead of re-encoding (faster, but only safe if every "
                         "clip has identical codec/resolution/frame rate - fine for a batch that "
                         "all came from the same autoedit.py --vertical run)")
    args = p.parse_args()

    if args.copy and args.target_duration:
        print("error: --copy and --target-duration can't be combined", file=sys.stderr)
        sys.exit(1)

    clips = sorted(
        c for c in args.input_dir.glob(args.pattern)
        if c.is_file() and c.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not clips:
        print(f"error: no clips matching {args.pattern!r} found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)
    if args.limit:
        clips = clips[:args.limit]

    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.target_duration:
        selected, total = select_for_target_duration(clips, args.target_duration)
        if not selected:
            print("error: no clips available to build the requested duration", file=sys.stderr)
            sys.exit(1)
        print(f"Using {len(selected)} clip(s), total {total:.1f}s (target {args.target_duration:.1f}s):", file=sys.stderr)
        for path, dur in selected:
            full = probe_duration(path)
            note = "full" if dur >= full - 0.05 else f"trimmed to {dur:.1f}s"
            print(f"  {path.name} ({note})", file=sys.stderr)
        if total < args.target_duration - 0.5:
            print(f"      note: only {total:.1f}s of edited footage available - "
                  f"couldn't reach the full {args.target_duration:.1f}s target.", file=sys.stderr)
        run_ffmpeg(build_trimmed_concat_cmd(selected, args.out))
        print(f"\nDone: {args.out}", file=sys.stderr)
        return

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
