#!/usr/bin/env python3
"""Turn a set of photos into an Instagram Reel (Ken Burns slideshow).

For businesses without raw video footage: given store/food photos, this
generates an actual vertical (1080x1920) video with a slow zoom/pan on
each photo, optional per-photo captions, and optional background music.
This is real video generation via ffmpeg - not AI text-to-video (this
environment has no access to that) - but it produces a genuine,
publishable Reel from still images.

Usage:
    python3 make_reel.py \
        --images photo1.jpg photo2.jpg photo3.jpg \
        --captions "本日のおすすめ" "自家製ケーキ" "ぜひお立ち寄りください" \
        --seconds-per-photo 3 \
        --music bgm.mp3 \
        --out reel.mp4

Captions are optional (omit --captions entirely, or pass fewer than
--images - remaining photos get no caption). Music is optional.
"""
import argparse
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

WIDTH, HEIGHT = 1080, 1920
FPS = 30

# CJK-capable fonts to try, in order, per OS. Override with --font if none
# of these exist on your machine.
DEFAULT_FONT_CANDIDATES = {
    "Windows": [
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/meiryob.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
    ],
    "Darwin": [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ],
    "Linux": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ],
}


def find_default_font():
    for candidate in DEFAULT_FONT_CANDIDATES.get(platform.system(), []):
        if Path(candidate).exists():
            return candidate
    return None


def escape_drawtext(text):
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def make_photo_clip(image_path, out_path, seconds, caption, zoom_direction, font_path):
    frames = int(seconds * FPS)
    # Ken Burns: scale up first so zoompan has room to pan, then zoom in
    # slowly over the clip's duration. Alternate zoom-in / pan direction
    # per photo so a multi-photo reel doesn't feel repetitive.
    if zoom_direction == "in":
        zoom_expr = f"min(zoom+0.0015,1.3)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        zoom_expr = f"if(lte(zoom,1.0),1.3,max(1.001,zoom-0.0015))"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"

    vf_parts = [
        f"scale={WIDTH*2}:{HEIGHT*2}:force_original_aspect_ratio=increase",
        f"crop={WIDTH*2}:{HEIGHT*2}",
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}",
    ]
    if caption:
        escaped = escape_drawtext(caption)
        escaped_font = escape_drawtext(str(font_path))
        vf_parts.append(
            f"drawtext=fontfile='{escaped_font}':"
            f"text='{escaped}':fontcolor=white:fontsize=54:"
            f"box=1:boxcolor=black@0.45:boxborderw=20:"
            f"x=(w-text_w)/2:y=h-320"
        )

    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-t", str(seconds),
        "-vf", ",".join(vf_parts),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        str(out_path),
    ], check=True, capture_output=True, text=True)


def concat_clips(clip_paths, out_path, work_dir):
    list_file = work_dir / "concat_list.txt"
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_paths))
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", str(out_path),
    ], check=True, capture_output=True, text=True)


def add_music(video_path, music_path, out_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path), "-stream_loop", "-1", "-i", str(music_path),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(out_path),
    ], check=True, capture_output=True, text=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--images", nargs="+", required=True, type=Path)
    p.add_argument("--captions", nargs="*", default=[])
    p.add_argument("--seconds-per-photo", type=float, default=3.0)
    p.add_argument("--music", type=Path, default=None)
    p.add_argument("--font", default=None,
                    help="Path to a CJK-capable font file for captions "
                         "(auto-detected per OS if omitted)")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    captions = list(args.captions) + [""] * (len(args.images) - len(args.captions))
    has_captions = any(captions)

    font_path = args.font or find_default_font()
    if has_captions and not font_path:
        print(
            "error: no caption text will render correctly - no CJK font found "
            "automatically for this OS. Pass --font <path to a .ttc/.ttf file> "
            "(e.g. C:/Windows/Fonts/YuGothB.ttc on Windows).",
            file=sys.stderr,
        )
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        clip_paths = []
        for i, (image, caption) in enumerate(zip(args.images, captions)):
            clip_path = work_dir / f"clip_{i:03d}.mp4"
            direction = "in" if i % 2 == 0 else "out"
            print(f"[{i+1}/{len(args.images)}] Rendering {image.name} ...", file=sys.stderr)
            make_photo_clip(image, clip_path, args.seconds_per_photo, caption, direction, font_path)
            clip_paths.append(clip_path)

        silent_path = work_dir / "silent.mp4"
        print("Concatenating clips...", file=sys.stderr)
        concat_clips(clip_paths, silent_path, work_dir)

        if args.music:
            print("Adding background music...", file=sys.stderr)
            add_music(silent_path, args.music, args.out)
        else:
            silent_path.replace(args.out)

    print(f"Done: {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
