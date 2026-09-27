#!/usr/bin/env python3
"""Turn a set of photos into a polished Instagram Reel (Ken Burns slideshow).

For businesses without raw video footage: given store/food photos, this
generates an actual vertical (1080x1920) video with a slow zoom/pan on
each photo, crossfade transitions, a subtle warm color grade + vignette,
fading captions, and optional branded intro/outro title cards and
background music.

This is real video generation via ffmpeg - not AI text-to-video, and not
a substitute for an actual TV commercial (no live-action cinematography,
actors, or professional sound design is possible from still photos alone)
- but it's the highest-polish version of a photo-to-video pipeline this
toolchain can produce: crossfades instead of hard cuts, color grading,
animated text, and branded open/close cards instead of a bare slideshow.

Usage:
    python3 make_reel.py \
        --images photo1.jpg photo2.jpg photo3.jpg \
        --captions "本日のおすすめ" "自家製ケーキ" "ぜひお立ち寄りください" \
        --seconds-per-photo 3 \
        --intro-title "喫茶すず" --intro-subtitle "昭和レトロな喫茶店" \
        --outro-title "ぜひお越しください" --outro-subtitle "@kissa_suzu123" \
        --music bgm.mp3 \
        --out reel.mp4

Captions are optional (omit --captions entirely, or pass fewer than
--images - remaining photos get no caption). Intro/outro cards and music
are all optional.
"""
import argparse
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WIDTH, HEIGHT = 1080, 1920
FPS = 30
TRANSITION_DURATION = 0.6
BRAND_BG = "0x241813"  # warm dark brown, matches a retro-cafe palette

# ffmpeg/ffprobe write UTF-8 to stdout/stderr regardless of platform, but on
# Japanese Windows the default locale encoding is cp932 (Shift-JIS), which
# can't decode every UTF-8 byte sequence ffmpeg produces - Python's
# subprocess reader threads crash with UnicodeDecodeError if we let them use
# that default. Force UTF-8 explicitly, replacing anything that still can't
# be decoded rather than crashing.
SUBPROCESS_TEXT_KWARGS = {"encoding": "utf-8", "errors": "replace"}

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


def run_ffmpeg(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_TEXT_KWARGS)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result


def find_default_font():
    for candidate in DEFAULT_FONT_CANDIDATES.get(platform.system(), []):
        if Path(candidate).exists():
            return candidate
    return None


def escape_drawtext(text):
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def fade_alpha_expr(seconds, fade=0.4, start_buffer=0.0, end_buffer=0.0):
    """A drawtext alpha expression that fades in, holds, then fades out.

    start_buffer/end_buffer reserve a fully-transparent window at each end
    of the clip - set these to the crossfade transition duration so a
    clip's caption is completely gone before the next clip's caption
    starts appearing, otherwise the two captions overlap into unreadable
    text during the crossfade.
    """
    fade_in_start = start_buffer
    fade_in_end = start_buffer + fade
    fade_out_end = seconds - end_buffer
    fade_out_start = fade_out_end - fade
    return (
        f"if(lt(t,{fade_in_start}),0,"
        f"if(lt(t,{fade_in_end}),(t-{fade_in_start})/{fade},"
        f"if(gt(t,{fade_out_end}),0,"
        f"if(gt(t,{fade_out_start}),({fade_out_end}-t)/{fade},1))))"
    )


def grade_and_vignette_filters():
    """Subtle warm color grade + vignette, applied to every clip so the
    whole reel reads as one graded piece rather than raw phone photos."""
    return [
        "eq=contrast=1.08:saturation=1.18:brightness=0.015",
        "colorbalance=rm=0.06:gm=0.0:bm=-0.08:rh=0.03:bh=-0.03",
        "vignette=PI/5",
    ]


def make_photo_clip(image_path, out_path, seconds, caption, zoom_direction, font_path,
                     start_buffer=0.0, end_buffer=0.0):
    frames = int(seconds * FPS)
    if zoom_direction == "in":
        zoom_expr = "min(zoom+0.0015,1.3)"
    else:
        zoom_expr = "if(lte(zoom,1.0),1.3,max(1.001,zoom-0.0015))"
    x_expr = "iw/2-(iw/zoom/2)"
    y_expr = "ih/2-(ih/zoom/2)"

    vf_parts = [
        f"scale={WIDTH*2}:{HEIGHT*2}:force_original_aspect_ratio=increase",
        f"crop={WIDTH*2}:{HEIGHT*2}",
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}",
        *grade_and_vignette_filters(),
    ]
    if caption:
        escaped = escape_drawtext(caption)
        escaped_font = escape_drawtext(str(font_path))
        alpha_expr = fade_alpha_expr(seconds, start_buffer=start_buffer, end_buffer=end_buffer)
        vf_parts.append(
            f"drawtext=fontfile='{escaped_font}':"
            f"text='{escaped}':fontcolor=white:fontsize=54:"
            f"box=1:boxcolor=black@0.45:boxborderw=20:"
            f"alpha='{alpha_expr}':"
            f"x=(w-text_w)/2:y=h-320"
        )

    run_ffmpeg([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-t", str(seconds),
        "-vf", ",".join(vf_parts),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(out_path),
    ])


def make_title_card(out_path, seconds, title, subtitle, font_path,
                     start_buffer=0.0, end_buffer=0.0):
    """A branded solid-color card with a fading-in title/subtitle, used
    for the intro and outro - the thing that makes this feel like a
    produced piece instead of a bare photo slideshow."""
    alpha_expr = fade_alpha_expr(seconds, fade=0.5, start_buffer=start_buffer, end_buffer=end_buffer)
    drawtext_common = f"fontfile='{escape_drawtext(str(font_path))}':alpha='{alpha_expr}'"

    vf_parts = [
        f"drawtext={drawtext_common}:text='{escape_drawtext(title)}':"
        f"fontcolor=white:fontsize=76:x=(w-text_w)/2:y=(h-text_h)/2-40"
    ]
    if subtitle:
        vf_parts.append(
            f"drawtext={drawtext_common}:text='{escape_drawtext(subtitle)}':"
            f"fontcolor=white@0.85:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2+60"
        )

    run_ffmpeg([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={BRAND_BG}:s={WIDTH}x{HEIGHT}:d={seconds}:r={FPS}",
        "-vf", ",".join(vf_parts),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(out_path),
    ])


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True, **SUBPROCESS_TEXT_KWARGS,
    )
    return float(out.stdout.strip())


def crossfade_concat(clip_paths, out_path, transition_duration):
    """Chain xfade across all clips so cuts are crossfades, not hard cuts."""
    if len(clip_paths) == 1:
        # No cp.exe on Windows - use shutil, not a subprocess.
        shutil.copy(str(clip_paths[0]), str(out_path))
        return

    durations = [probe_duration(p) for p in clip_paths]
    cmd = ["ffmpeg", "-y"]
    for p in clip_paths:
        cmd += ["-i", str(p)]

    filter_parts = []
    running_duration = durations[0]
    prev_label = "0:v"
    for i in range(1, len(clip_paths)):
        offset = running_duration - transition_duration
        out_label = f"v{i}" if i < len(clip_paths) - 1 else "vout"
        filter_parts.append(
            f"[{prev_label}][{i}:v]xfade=transition=fade:"
            f"duration={transition_duration}:offset={offset:.3f}[{out_label}]"
        )
        running_duration = running_duration + durations[i] - transition_duration
        prev_label = out_label

    filter_complex = ";".join(filter_parts)
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    run_ffmpeg(cmd)


def add_music_with_fadeout(video_path, music_path, out_path, video_duration):
    fade_start = max(0.0, video_duration - 1.5)
    run_ffmpeg([
        "ffmpeg", "-y", "-i", str(video_path), "-stream_loop", "-1", "-i", str(music_path),
        "-map", "0:v", "-map", "1:a",
        "-af", f"afade=t=out:st={fade_start:.2f}:d=1.5",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(out_path),
    ])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--images", nargs="+", required=True, type=Path)
    p.add_argument("--captions", nargs="*", default=[])
    p.add_argument("--seconds-per-photo", type=float, default=3.0)
    p.add_argument("--intro-title", default=None)
    p.add_argument("--intro-subtitle", default=None)
    p.add_argument("--intro-seconds", type=float, default=2.0)
    p.add_argument("--outro-title", default=None)
    p.add_argument("--outro-subtitle", default=None)
    p.add_argument("--outro-seconds", type=float, default=2.2)
    p.add_argument("--transition-duration", type=float, default=TRANSITION_DURATION)
    p.add_argument("--no-transitions", action="store_true", help="Hard cuts instead of crossfades")
    p.add_argument("--music", type=Path, default=None)
    p.add_argument("--font", default=None,
                    help="Path to a CJK-capable font file for captions "
                         "(auto-detected per OS if omitted)")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    captions = list(args.captions) + [""] * (len(args.images) - len(args.captions))
    has_text = any(captions) or args.intro_title or args.outro_title

    font_path = args.font or find_default_font()
    if has_text and not font_path:
        print(
            "error: no caption/title text will render correctly - no CJK font "
            "found automatically for this OS. Pass --font <path to a .ttc/.ttf "
            "file> (e.g. C:/Windows/Fonts/YuGothB.ttc on Windows).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build the full clip plan first so each clip knows whether it's at the
    # very start/end of the whole video (no transition buffer needed there)
    # or has a crossfade neighbor on one or both sides (buffer needed, so
    # captions don't overlap into unreadable text during the transition).
    plan = []
    if args.intro_title:
        plan.append(("title", (args.intro_seconds, args.intro_title, args.intro_subtitle)))
    for image, caption in zip(args.images, captions):
        plan.append(("photo", (image, args.seconds_per_photo, caption)))
    if args.outro_title:
        plan.append(("title", (args.outro_seconds, args.outro_title, args.outro_subtitle)))

    transition_buffer = 0.0 if args.no_transitions else args.transition_duration

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        clip_paths = []
        photo_i = 0

        for idx, (kind, spec) in enumerate(plan):
            start_buffer = 0.0 if idx == 0 else transition_buffer
            end_buffer = 0.0 if idx == len(plan) - 1 else transition_buffer
            clip_path = work_dir / f"clip_{idx:03d}.mp4"

            if kind == "title":
                seconds, title, subtitle = spec
                print(f"Rendering title card ({title!r})...", file=sys.stderr)
                make_title_card(clip_path, seconds, title, subtitle, font_path,
                                 start_buffer=start_buffer, end_buffer=end_buffer)
            else:
                image, seconds, caption = spec
                direction = "in" if photo_i % 2 == 0 else "out"
                photo_i += 1
                print(f"[{photo_i}/{len(args.images)}] Rendering {image.name} ...", file=sys.stderr)
                make_photo_clip(image, clip_path, seconds, caption, direction, font_path,
                                 start_buffer=start_buffer, end_buffer=end_buffer)

            clip_paths.append(clip_path)

        silent_path = work_dir / "silent.mp4"
        if args.no_transitions:
            print("Concatenating clips (hard cuts)...", file=sys.stderr)
            list_file = work_dir / "concat_list.txt"
            list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_paths))
            run_ffmpeg([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                "-c", "copy", str(silent_path),
            ])
        else:
            print("Combining clips with crossfade transitions...", file=sys.stderr)
            crossfade_concat(clip_paths, silent_path, args.transition_duration)

        if args.music:
            print("Adding background music...", file=sys.stderr)
            final_duration = probe_duration(silent_path)
            add_music_with_fadeout(silent_path, args.music, args.out, final_duration)
        else:
            silent_path.replace(args.out)

    print(f"Done: {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
