# photo_reel

Generates an actual Instagram Reel (1080x1920 MP4) from a set of photos,
for when there's no raw video footage to edit yet. Applies a Ken Burns
zoom/pan effect to each photo, optional burned-in captions, and optional
looped background music.

This is **not** AI text-to-video generation (no such model is available
in this environment) - it's a real, working ffmpeg pipeline that turns
still photos into a publishable slideshow-style Reel. Validated with a
3-photo test: confirmed 1080x1920 output, correct per-photo duration, and
readable Japanese captions burned in (checked by extracting frames).

## Setup

Same as `tools/autoedit/` - needs `ffmpeg`:

```bash
# Windows: winget install ffmpeg   (see tools/autoedit/README.md)
```

Japanese captions need a CJK-capable font. The script auto-detects a
common one for your OS (Yu Gothic Bold on Windows, Hiragino on macOS,
Noto Sans CJK on Linux). If none of those are found, or you want a
different one, pass `--font "C:/Windows/Fonts/YuGothB.ttc"` (or wherever
your font file lives).

## Usage

```bash
python3 tools/photo_reel/make_reel.py \
  --images 店舗外観.jpg 料理1.jpg 料理2.jpg 店内.jpg \
  --captions "喫茶すず" "自家製ケーキ" "本日のおすすめ" "お待ちしております" \
  --seconds-per-photo 3 \
  --music bgm.mp3 \
  --out reel.mp4
```

| Flag | Meaning |
|---|---|
| `--images` | Photo files, in the order they should appear (required) |
| `--captions` | One caption per photo, same order (optional - omit entirely, or give fewer than `--images` and the rest get no caption) |
| `--seconds-per-photo` | How long each photo is shown (default 3s) |
| `--music` | A royalty-free / your own audio track, looped and trimmed to the video's length (optional) |
| `--out` | Output video path (required) |

## Notes

- Alternates zoom-in / zoom-out per photo so a multi-photo reel doesn't
  feel repetitive.
- Photos are scaled up and center-cropped to fill the 9:16 frame - very
  wide or very tall source photos will lose some edge content.
- For music, use something you have the rights to use commercially (a
  royalty-free library track, or your own recording) - this script
  doesn't check licensing.
- **Avoid emoji in `--captions`.** The CJK fonts above don't include emoji
  glyphs, so an emoji renders as a broken/empty box instead of the emoji
  itself (found this the hard way on a real caption with ☕). Stick to
  plain text.
