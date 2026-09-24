#!/usr/bin/env python3
"""End-to-end pipeline: edit new footage, build a draft reel, upload it, post to Instagram.

Ties together the pieces already built in this repo:
  1. autoedit.py       - silence cut + captions + vertical crop, batch mode
                          (skips clips already edited from a previous run)
  2. concat_edited.py  - pick ~target_duration_seconds of *newly* edited
                          clips (not already posted) and trim the last one
                          to land on the target length
  3. upload_to_supabase.py - upload the draft to a public Supabase Storage
                          bucket, since Instagram's API needs a public URL
  4. publish_reel.py   - create the media container, wait for processing,
                          publish it as a Reel

Meant to be run unattended on a schedule (Windows Task Scheduler) so new
raw footage dropped into raw_dir gets edited and posted automatically.
tools/pipeline/posted_state.json tracks which edited clips have already
gone out in a previous post, so the same footage is never reused.

Setup (one-time):
    1. Copy config.example.json to config.local.json (same folder) and
       fill in the real secrets. config.local.json is gitignored - never
       commit it.
    2. pip install -r tools/autoedit/requirements.txt requests

Usage:
    python3 tools/pipeline/auto_post.py --config tools/pipeline/config.local.json
    python3 tools/pipeline/auto_post.py --config tools/pipeline/config.local.json --dry-run
        (does the edit/build/upload steps but stops before actually
        publishing to Instagram - use this to sanity-check a new setup)
"""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "autoedit"))
sys.path.insert(0, str(HERE.parent / "instagram_publish"))

from concat_edited import select_for_target_duration, build_trimmed_concat_cmd, run_ffmpeg  # noqa: E402
from publish_reel import create_container, wait_until_ready, publish  # noqa: E402
from upload_to_supabase import upload as upload_to_supabase  # noqa: E402

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
DEFAULT_STATE_PATH = HERE / "posted_state.json"


def load_json(path, default):
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_autoedit_batch(raw_dir, edited_dir, lang):
    print("=== [1/4] Editing any new raw footage ===", file=sys.stderr)
    autoedit_py = HERE.parent / "autoedit" / "autoedit.py"
    subprocess.run(
        [sys.executable, str(autoedit_py), "--input-dir", str(raw_dir), "--out", str(edited_dir),
         "--vertical", "--lang", lang],
        check=True,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=HERE / "config.local.json")
    p.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    p.add_argument("--dry-run", action="store_true",
                    help="Do everything except actually publish to Instagram")
    args = p.parse_args()

    if not args.config.exists():
        print(f"error: config file not found: {args.config}\n"
              f"Copy tools/pipeline/config.example.json to that path and fill in your secrets.",
              file=sys.stderr)
        sys.exit(1)
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    state = load_json(args.state, {"posted_clips": []})

    raw_dir = Path(cfg["raw_dir"])
    edited_dir = Path(cfg["edited_dir"])
    target_duration = float(cfg.get("target_duration_seconds", 30))

    run_autoedit_batch(raw_dir, edited_dir, cfg.get("lang", "ja"))

    print("\n=== [2/4] Selecting new clips for a draft ===", file=sys.stderr)
    already_posted = set(state.get("posted_clips", []))
    all_clips = sorted(
        c for c in edited_dir.glob("*_edited.mp4")
        if c.is_file() and c.suffix.lower() in VIDEO_EXTENSIONS
    )
    new_clips = [c for c in all_clips if c.name not in already_posted]
    if not new_clips:
        print("No new edited clips since the last post. Nothing to do.", file=sys.stderr)
        return

    selected, total = select_for_target_duration(new_clips, target_duration)
    if not selected:
        print("No usable new footage yet. Nothing to do.", file=sys.stderr)
        return
    print(f"Using {len(selected)} new clip(s), {total:.1f}s total:", file=sys.stderr)
    for path, dur in selected:
        print(f"  {path.name} ({dur:.1f}s)", file=sys.stderr)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    draft_path = edited_dir / f"draft_{timestamp}.mp4"
    run_ffmpeg(build_trimmed_concat_cmd(selected, draft_path))
    print(f"Draft built: {draft_path}", file=sys.stderr)

    print("\n=== [3/4] Uploading draft for a public URL ===", file=sys.stderr)
    public_url = upload_to_supabase(
        cfg["supabase_url"], cfg["supabase_service_key"], cfg["supabase_bucket"],
        draft_path, draft_path.name,
    )
    print(f"Public URL: {public_url}", file=sys.stderr)

    if args.dry_run:
        print("\n--dry-run: skipping the actual Instagram publish step.", file=sys.stderr)
        return

    print("\n=== [4/4] Publishing to Instagram ===", file=sys.stderr)
    caption = cfg.get("caption_template", "")
    creation_id = create_container(cfg["ig_user_id"], public_url, caption, cfg["ig_page_token"])
    print(f"   container id: {creation_id}", file=sys.stderr)
    wait_until_ready(creation_id, cfg["ig_page_token"])
    media_id = publish(cfg["ig_user_id"], creation_id, cfg["ig_page_token"])
    print(f"Published. Media ID: {media_id}", file=sys.stderr)

    state["posted_clips"] = sorted(already_posted | {c.name for c, _ in selected})
    save_json(args.state, state)
    print("State updated - these clips won't be reused in a future post.", file=sys.stderr)


if __name__ == "__main__":
    main()
