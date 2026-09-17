#!/usr/bin/env python3
"""Real AI video auto-editor: silence/filler cutting + auto captions + 9:16 export.

This is the actual implementation behind the "AI automatically edits your
footage" promise made by the ReelCraft AI / VidFlow AI landing pages in
this repo (those were marketing mockups only). Given one raw video file,
this script:

  1. Transcribes the audio (faster-whisper, runs locally/offline).
  2. Uses the speech segments to find and cut out silence/dead air.
  3. Re-transcribes the cut video so caption timing lines up exactly.
  4. Burns in Japanese-capable captions.
  5. Optionally crops/scales to 9:16 for Reels/Shorts/TikTok.

Requires: ffmpeg/ffprobe, and `pip install faster-whisper` (see
tools/autoedit/requirements.txt). All processing is local; no video or
audio data is sent to any external API.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from faster_whisper import WhisperModel

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}

# ffmpeg/ffprobe write UTF-8 to stdout/stderr regardless of platform, but on
# Japanese Windows the default locale encoding is cp932 (Shift-JIS), which
# can't decode every UTF-8 byte sequence ffmpeg produces - Python's
# subprocess reader threads crash with UnicodeDecodeError if we let them use
# that default. Force UTF-8 explicitly, replacing anything that still can't
# be decoded rather than crashing.
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


def transcribe(path, model_name, language):
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(path), language=language, vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
    )
    return [
        {"start": s.start, "end": s.end, "text": s.text.strip()}
        for s in segments if s.text.strip()
    ]


def build_keep_ranges(segments, duration, pad=0.15, merge_gap=0.35):
    """Speech segments, padded slightly and merged when close together."""
    if not segments:
        return [(0.0, duration)]

    ranges = []
    for seg in segments:
        start = max(0.0, seg["start"] - pad)
        end = min(duration, seg["end"] + pad)
        ranges.append([start, end])

    merged = [ranges[0]]
    for start, end in ranges[1:]:
        if start - merged[-1][1] <= merge_gap:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(round(s, 3), round(e, 3)) for s, e in merged]


def cut_silence(input_path, keep_ranges, output_path):
    n = len(keep_ranges)
    if n == 1 and keep_ranges[0][0] == 0.0:
        # Nothing to cut. Use shutil, not a `cp` subprocess - there's no
        # cp.exe on Windows.
        shutil.copy(str(input_path), str(output_path))
        return

    filter_parts = []
    v_labels, a_labels = [], []
    for i, (start, end) in enumerate(keep_ranges):
        filter_parts.append(
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]"
        )
        filter_parts.append(
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]"
        )
        v_labels.append(f"[v{i}]")
        a_labels.append(f"[a{i}]")

    concat_inputs = "".join(f"{v}{a}" for v, a in zip(v_labels, a_labels))
    filter_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=1[outv][outa]")
    filter_complex = ";".join(filter_parts)

    run_ffmpeg([
        "ffmpeg", "-y", "-i", str(input_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ])


def srt_timestamp(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments, path, max_chars=22):
    lines = []
    idx = 1
    for seg in segments:
        text = seg["text"]
        chunks = [text[i:i + max_chars] for i in range(0, len(text), max_chars)] or [text]
        span = seg["end"] - seg["start"]
        per_chunk = span / len(chunks)
        for i, chunk in enumerate(chunks):
            start = seg["start"] + i * per_chunk
            end = start + per_chunk
            lines.append(str(idx))
            lines.append(f"{srt_timestamp(start)} --> {srt_timestamp(end)}")
            lines.append(chunk)
            lines.append("")
            idx += 1
    path.write_text("\n".join(lines), encoding="utf-8")


def render_final(cut_path, srt_path, output_path, vertical, burn_captions):
    vf_parts = []
    if vertical:
        vf_parts.append("scale=1080:1920:force_original_aspect_ratio=increase")
        vf_parts.append("crop=1080:1920")
    if burn_captions:
        escaped = str(srt_path).replace(":", "\\:")
        vf_parts.append(
            f"subtitles={escaped}:force_style="
            "'FontName=Noto Sans CJK JP,FontSize=13,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H90000000,BorderStyle=3,Outline=2,"
            "Alignment=2,MarginV=90'"
        )

    cmd = ["ffmpeg", "-y", "-i", str(cut_path)]
    if vf_parts:
        cmd += ["-vf", ",".join(vf_parts)]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", str(output_path)]
    run_ffmpeg(cmd)


def process_video(input_path, out_path, srt_path, args):
    work_dir = out_path.parent / f".{out_path.stem}_autoedit_tmp"
    work_dir.mkdir(parents=True, exist_ok=True)
    cut_path = work_dir / "cut.mp4"
    srt_path = srt_path or out_path.with_suffix(".srt")

    try:
        duration = probe_duration(input_path)
        needs_initial_transcribe = not args.no_cut or not args.no_captions
        segments = []
        if needs_initial_transcribe:
            print(f"[1/4] Transcribing {input_path.name} ...", file=sys.stderr)
            segments = transcribe(input_path, args.model, args.lang)
            print(f"      {len(segments)} speech segments found in {duration:.1f}s of source.", file=sys.stderr)

        if args.no_cut:
            cut_path = input_path
        else:
            print("[2/4] Removing silence/dead air ...", file=sys.stderr)
            keep_ranges = build_keep_ranges(segments, duration)
            cut_silence(input_path, keep_ranges, cut_path)
            cut_duration = probe_duration(cut_path)
            print(f"      {duration:.1f}s -> {cut_duration:.1f}s (removed {duration - cut_duration:.1f}s)", file=sys.stderr)

        if not args.no_captions:
            print("[3/4] Re-transcribing cut video for caption sync ...", file=sys.stderr)
            final_segments = transcribe(cut_path, args.model, args.lang) if not args.no_cut else segments
            write_srt(final_segments, srt_path)
            print(f"      captions written to {srt_path}", file=sys.stderr)

        print("[4/4] Rendering final video ...", file=sys.stderr)
        render_final(cut_path, srt_path, out_path, args.vertical, not args.no_captions)
        print(f"Done: {out_path}", file=sys.stderr)
    finally:
        if not args.keep_intermediate:
            if cut_path != input_path:
                cut_path.unlink(missing_ok=True)
            try:
                work_dir.rmdir()
            except OSError:
                pass


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path, nargs="?", help="Raw input video (omit when using --input-dir)")
    p.add_argument("--input-dir", type=Path, default=None,
                    help="Process every video file in this directory instead of a single file")
    p.add_argument("--out", type=Path, required=True,
                    help="Final output video path (single-file mode) or output directory (--input-dir mode)")
    p.add_argument("--srt", type=Path, default=None,
                    help="Where to save captions (.srt) - single-file mode only")
    p.add_argument("--lang", default="ja", help="Language code for transcription (default: ja)")
    p.add_argument("--model", default="small", help="faster-whisper model size (tiny/base/small/medium)")
    p.add_argument("--vertical", action="store_true", help="Crop/scale to 1080x1920 (9:16) for Reels/Shorts")
    p.add_argument("--no-captions", action="store_true", help="Don't burn in captions")
    p.add_argument("--no-cut", action="store_true", help="Skip silence removal")
    p.add_argument("--keep-intermediate", action="store_true")
    args = p.parse_args()

    if bool(args.input) == bool(args.input_dir):
        print("error: pass exactly one of <input> or --input-dir", file=sys.stderr)
        sys.exit(1)

    if args.input:
        process_video(args.input, args.out, args.srt, args)
        return

    args.out.mkdir(parents=True, exist_ok=True)
    videos = sorted(
        f for f in args.input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not videos:
        print(f"error: no video files found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(videos)} video(s) in {args.input_dir}", file=sys.stderr)
    succeeded, failed = [], []
    for i, video in enumerate(videos, 1):
        out_path = args.out / f"{video.stem}_edited.mp4"
        print(f"\n=== [{i}/{len(videos)}] {video.name} ===", file=sys.stderr)
        try:
            process_video(video, out_path, None, args)
            succeeded.append(video.name)
        except Exception as e:
            print(f"FAILED on {video.name}: {e}", file=sys.stderr)
            failed.append(video.name)

    print(f"\nDone: {len(succeeded)} succeeded, {len(failed)} failed.", file=sys.stderr)
    if failed:
        print("Failed files:\n  " + "\n  ".join(failed), file=sys.stderr)


if __name__ == "__main__":
    main()
