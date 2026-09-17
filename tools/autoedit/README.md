# autoedit — the real video auto-editing engine

This is an actual, working implementation of the automatic editing that the
`ReelCraft AI` / `VidFlow AI` landing pages in this repo describe. Those
pages are marketing mockups; this tool is the real thing, running entirely
locally with `ffmpeg` and `faster-whisper` — no video/audio is uploaded to
any third-party API.

## What it actually does

Given one raw video file:

1. Transcribes the audio locally (`faster-whisper`, runs on CPU).
2. Uses the speech segments to detect and cut out silence/dead air.
3. Re-transcribes the cut video so caption timing lines up exactly.
4. Burns in Japanese-capable captions (`.srt` is also saved separately).
5. Optionally center-crops/scales to 1080x1920 (9:16) for Reels/Shorts/TikTok.

This was validated end-to-end against a synthetic Japanese test video
(silence + speech clips): a 38s source was correctly cut to 31.4s, vertical
1080x1920 export confirmed, and burned-in Japanese captions confirmed
visually by extracting frames from the output.

## Setup

```bash
apt-get install -y ffmpeg fonts-noto-cjk   # video processing + CJK subtitle rendering
pip install -r tools/autoedit/requirements.txt
```

The first run of `faster-whisper` downloads its model from Hugging Face
(a few hundred MB, one-time, then cached under `~/.cache/huggingface`).
**This requires outbound network access to `huggingface.co`.** In this
project's current sandboxed session, that host is blocked by the egress
proxy's org policy (confirmed via `curl $HTTPS_PROXY/__agentproxy/status`),
so the speech-to-text step could not be exercised end-to-end here — only
the surrounding ffmpeg pipeline (cutting/captioning/resizing) was validated,
using a stubbed transcript. On an unrestricted machine (a normal laptop/
server, or a session whose egress policy allows huggingface.co) the whole
pipeline runs as-is.

## Usage

Single file:

```bash
python3 tools/autoedit/autoedit.py raw_source.mp4 \
  --out reel_final.mp4 \
  --vertical \
  --lang ja
```

Batch mode - process every video in a folder (e.g. a phone's whole camera
roll dumped into one directory):

```bash
python3 tools/autoedit/autoedit.py --input-dir raw_videos --out edited_videos --vertical --lang ja
```

Each `<name>.mp4`/`.mov`/etc. in `raw_videos` becomes
`edited_videos/<name>_edited.mp4`. One bad/corrupt file doesn't stop the
rest - failures are logged and summarized at the end (`N succeeded, M
failed`).

Options:

| Flag | Meaning |
|---|---|
| `input` | Single raw input video (omit when using `--input-dir`) |
| `--input-dir DIR` | Process every video file in this directory instead of one file |
| `--out PATH` | Final output video (single-file mode) or output directory (`--input-dir` mode) (required) |
| `--srt PATH` | Where to save captions (default: `<out>.srt`) - single-file mode only |
| `--lang ja` | Transcription language (default `ja`) |
| `--model small` | `faster-whisper` model size: `tiny`/`base`/`small`/`medium` |
| `--vertical` | Crop/scale to 1080x1920 for Reels/Shorts/TikTok |
| `--no-captions` | Skip burning in captions |
| `--no-cut` | Skip silence removal |
| `--keep-intermediate` | Keep the intermediate silence-cut file for debugging |

With ~100 videos, expect this to take a while - each file does two
transcription passes (before and after the silence cut) plus the final
render. Let it run; it won't need attention until it's done or a file
fails.

## Known limitations (be upfront about these)

- Cuts on **silence**, not on filler words (「えー」「あの」) specifically —
  those are usually followed by a brief pause anyway, so they often get
  swept up in a silence cut, but there's no dedicated filler-word detector.
- No highlight/best-moment detection, no BGM, no multi-pattern generation,
  no natural-language re-edit instructions — those are still ReelCraft AI /
  VidFlow AI marketing concepts, not implemented here.
- Vertical export always center-crops (no subject tracking) — fine for a
  static talking-head shot, less fine for footage where the subject moves
  to the frame edges.
