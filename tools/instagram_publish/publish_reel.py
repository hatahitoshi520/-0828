#!/usr/bin/env python3
"""Publish a video as an Instagram Reel via the Meta Graph API.

Must be run from a machine with normal internet access - this repo's dev
sandbox cannot reach graph.facebook.com due to its network policy.

The video must already be at a public HTTPS URL (Instagram's servers fetch
it from there) - e.g. uploaded to Supabase Storage, or any other public
host. This script does not upload the video itself.

Usage:
    pip install requests
    python3 publish_reel.py \
        --page-token "<page access token>" \
        --ig-user-id 17841478716095901 \
        --video-url "https://.../video.mp4" \
        --caption "投稿文 #ハッシュタグ"

The page token and IG user ID were obtained during the one-time Meta app
setup (see docs/instagram-setup.md). The page token is long-lived (~60
days); regenerate it via the same Graph API Explorer flow once it expires.
"""
import argparse
import sys
import time

import requests

API_VERSION = "v25.0"
GRAPH_URL = f"https://graph.facebook.com/{API_VERSION}"


def create_container(ig_user_id, video_url, caption, page_token):
    resp = requests.post(f"{GRAPH_URL}/{ig_user_id}/media", data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": page_token,
    })
    resp.raise_for_status()
    return resp.json()["id"]


def wait_until_ready(creation_id, page_token, poll_interval=5, max_attempts=60):
    for attempt in range(1, max_attempts + 1):
        time.sleep(poll_interval)
        resp = requests.get(f"{GRAPH_URL}/{creation_id}", params={
            "fields": "status_code,status",
            "access_token": page_token,
        })
        resp.raise_for_status()
        data = resp.json()
        print(f"   [{attempt}/{max_attempts}] status: {data['status_code']}", file=sys.stderr)
        if data["status_code"] == "FINISHED":
            return
        if data["status_code"] == "ERROR":
            raise RuntimeError(f"Instagram failed to process the video: {data.get('status')}")
    raise TimeoutError("Timed out waiting for Instagram to finish processing the video")


def publish(ig_user_id, creation_id, page_token):
    resp = requests.post(f"{GRAPH_URL}/{ig_user_id}/media_publish", data={
        "creation_id": creation_id,
        "access_token": page_token,
    })
    resp.raise_for_status()
    return resp.json()["id"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--page-token", required=True)
    p.add_argument("--ig-user-id", required=True)
    p.add_argument("--video-url", required=True)
    p.add_argument("--caption", required=True)
    args = p.parse_args()

    print("1/3: Creating media container...", file=sys.stderr)
    creation_id = create_container(args.ig_user_id, args.video_url, args.caption, args.page_token)
    print(f"   container id: {creation_id}", file=sys.stderr)

    print("2/3: Waiting for Instagram to finish processing the video...", file=sys.stderr)
    wait_until_ready(creation_id, args.page_token)

    print("3/3: Publishing...", file=sys.stderr)
    media_id = publish(args.ig_user_id, creation_id, args.page_token)

    print(f"Published. Media ID: {media_id}")


if __name__ == "__main__":
    main()
