#!/usr/bin/env python3
"""Upload a local video to a public Supabase Storage bucket and print its URL.

Instagram's Graph API needs a publicly reachable HTTPS URL to fetch the
video from - it does not accept a direct file upload (see publish_reel.py).
This uploads to a Supabase Storage bucket for exactly that purpose. Must be
run from a machine with normal internet access (this repo's dev sandbox
cannot reach Supabase's Storage REST API).

Usage:
    pip install requests
    python3 upload_to_supabase.py \
        --supabase-url https://<project-ref>.supabase.co \
        --service-key "<key - see below>" \
        --file "C:\\...\\draft_30s.mp4" \
        --bucket reels

Despite the flag name, this doesn't require the (secret) service_role key
- a Row Level Security policy on storage.objects grants insert/update on
just the target bucket to the anon role, so the project's public legacy
anon key (a JWT starting eyJhbGci..., from Supabase dashboard -> Project
Settings -> API -> Legacy API Keys) works and is not a secret. See
tools/pipeline/README.md for why (this project's storage endpoint rejects
the newer sb_secret_... key format with "Invalid Compact JWS").
"""
import argparse
import sys
from pathlib import Path

import requests


def upload(supabase_url, service_key, bucket, local_path, dest_name):
    local_path = Path(local_path)
    url = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{dest_name}"
    with open(local_path, "rb") as f:
        resp = requests.post(
            url,
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "video/mp4",
                "x-upsert": "true",
            },
            data=f,
        )
    if resp.status_code >= 400:
        # Surface the response body - Supabase Storage puts the actual
        # reason here (e.g. "Invalid Compact JWS" for a bad/expired key,
        # or a row-level-security violation if the key isn't service_role)
        # and requests.raise_for_status() alone throws it away.
        print(f"Supabase Storage returned {resp.status_code}: {resp.text}", file=sys.stderr)
    resp.raise_for_status()
    return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket}/{dest_name}"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--supabase-url", required=True)
    p.add_argument("--service-key", required=True)
    p.add_argument("--bucket", default="reels")
    p.add_argument("--file", required=True, type=Path)
    p.add_argument("--dest-name", default=None,
                    help="Object name inside the bucket (default: the local filename)")
    args = p.parse_args()

    dest_name = args.dest_name or args.file.name
    print(f"Uploading {args.file} -> {args.bucket}/{dest_name} ...", file=sys.stderr)
    public_url = upload(args.supabase_url, args.service_key, args.bucket, args.file, dest_name)
    print(public_url)


if __name__ == "__main__":
    main()
