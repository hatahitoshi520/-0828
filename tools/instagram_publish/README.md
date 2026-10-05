# instagram_publish

Publishes a video as a Reel to `@kissa_suzu123` via the Meta Graph API.

## Why this can't run in this dev sandbox

This repo's Claude Code sandbox has an outbound network policy that blocks
`graph.facebook.com` (and also blocks direct uploads to Supabase Storage
from this sandbox). Both were confirmed blocked with a 403 at the proxy
level, not a code bug. So the scripts here are meant to be run from your
own PC (or any machine with normal internet access), not from this
sandbox.

## What you need before running this

1. **A long-lived Page access token** and the **Instagram Business Account
   ID**, obtained once via the Meta app / Graph API Explorer setup (see
   `docs/instagram-setup.md` for the IDs and what was configured; the
   token itself is a secret - keep it out of git, out of chat logs going
   forward, and out of any file in this repo).
2. **The video already at a public HTTPS URL.** Instagram's servers fetch
   the video from that URL - it does not accept a local file upload
   directly. Options:
   - Upload it via the Supabase dashboard (Storage → your bucket → Upload)
     and copy the public object URL.
   - Any other public host (a CDN, S3 bucket with public read, etc.)

## Usage

PowerShell (Windows - matches the setup you already did in Graph API
Explorer):

```powershell
cd tools/instagram_publish
.\publish_reel.ps1 `
  -PageToken "<your page access token>" `
  -IgUserId "17841478716095901" `
  -VideoUrl "https://.../your-edited-video.mp4" `
  -Caption "本日のおすすめ🍰 #喫茶すず #カフェ"
```

Python (any OS):

```bash
pip install requests
python3 publish_reel.py \
  --page-token "<your page access token>" \
  --ig-user-id 17841478716095901 \
  --video-url "https://.../your-edited-video.mp4" \
  --caption "本日のおすすめ🍰 #喫茶すず #カフェ"
```

Either script: creates a media container (`media_type=REELS`), polls until
Instagram finishes processing the video, then publishes it. Takes roughly
30 seconds to a few minutes depending on video length.

## Token expiry

The page token is long-lived (~60 days from issue). When it expires,
regenerate it the same way as the initial setup: Graph API Explorer →
Generate Access Token → exchange for a long-lived token → look up the page
token via the page ID. See `docs/instagram-setup.md` for the exact IDs
involved.
