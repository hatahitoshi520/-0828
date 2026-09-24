# auto_post — hands-off editing + Instagram posting

Ties together everything else in `tools/` into one pipeline you can run
unattended: edit any new raw footage, build a ~30s draft from clips that
haven't been posted yet, upload it somewhere public, and publish it to
`@kissa_suzu123` as a Reel.

```
raw footage  ->  autoedit.py (batch)  ->  concat_edited.py (~30s of NEW clips)
             ->  upload_to_supabase.py (public URL)  ->  publish_reel.py (Instagram)
```

Each new run only uses edited clips that haven't gone into a previous post
(`posted_state.json` tracks this) - so running it daily on a folder that
keeps getting new phone footage dropped into it naturally produces a new,
never-repeated Reel each time there's enough new material.

## One-time setup

1. **Copy the config template** and fill in the real values:

   ```powershell
   copy tools\pipeline\config.example.json tools\pipeline\config.local.json
   ```

   `config.local.json` is gitignored - it holds secrets and must never be
   committed. Edit it:

   | Field | Where to get it |
   |---|---|
   | `raw_dir` | Folder where new raw phone footage lands |
   | `edited_dir` | Where autoedit.py's output goes (same as your existing batch runs) |
   | `target_duration_seconds` | How long each posted draft should be (default 30) |
   | `supabase_url` | Already filled in - the `hatahitoshi0520@icloud.com` Supabase project. A public `reels` storage bucket has already been created there for this. |
   | `supabase_service_key` | Supabase dashboard -> that project -> Project Settings -> API. Use the **Legacy API Keys** section's `service_role` key (the long `eyJhbGci...` JWT string) - **not** the newer `sb_secret_...` key from the "API Keys" section. This project's storage endpoint currently rejects the new key format with `Invalid Compact JWS`. **Secret** - bypasses all access rules, keep it only in this local file. |
   | `ig_user_id` | Already filled in (`17841478716095901`, see `docs/instagram-setup.md`) |
   | `ig_page_token` | The current page access token - see "Regenerating the page access token" in `docs/instagram-setup.md`. **Expires roughly every 60 days** - when the pipeline starts failing at the publish step, this is almost always why. |
   | `caption_template` | Fixed caption/hashtags used on every post - edit to taste |

2. **Install dependencies** (once):

   ```powershell
   pip install -r tools\autoedit\requirements.txt requests
   ```

3. **Test it without actually posting**:

   ```powershell
   python tools\pipeline\auto_post.py --config tools\pipeline\config.local.json --dry-run
   ```

   This runs the real edit + draft-build + upload steps (so you can check
   the printed public URL actually plays in a browser) but stops before
   touching Instagram. Confirms your Supabase key and paths are right
   before anything goes live.

4. **Run it for real once**, by hand, and check the post shows up on
   `@kissa_suzu123`:

   ```powershell
   python tools\pipeline\auto_post.py --config tools\pipeline\config.local.json
   ```

## Making it fully automatic

Once step 4 above has posted successfully, register a scheduled task so
this runs on its own (e.g. once a day) with no one at the keyboard:

```powershell
schtasks /create /tn "KissaSuzuAutoPost" /sc daily /st 09:00 /tr "python C:\Users\81708\-0828\tools\pipeline\auto_post.py --config C:\Users\81708\-0828\tools\pipeline\config.local.json"
```

(Run `where python` first and use that full path in `/tr` if `python` alone
doesn't resolve for Task Scheduler - it doesn't always inherit your normal
PATH.)

**Before you do this, understand what it means**: from that point on, any
new footage you drop into `raw_dir` gets edited and posted to the real,
public `@kissa_suzu123` account automatically, with nothing to review
first. There's no draft-approval step. If you'd rather review each draft
before it goes live, skip the scheduled task and just run the command from
step 4 manually whenever you want to post - everything above it (editing,
picking new clips, building the draft) still saves you all the manual work,
you just add one manual "yes, post this" step.

To turn off the automation later: `schtasks /delete /tn "KissaSuzuAutoPost" /f`

## Known limitations

- **The page token expires (~60 days)** and there's no automated refresh -
  Meta's flow requires a human in the Graph API Explorer. When it expires,
  scheduled runs will fail at the publish step until you regenerate it
  (`docs/instagram-setup.md`) and update `config.local.json`.
- **No failure notifications.** A scheduled run that fails just fails
  silently in the background (check Task Scheduler's history, or run it
  by hand occasionally to make sure it's still working).
- **No highlight/best-take selection** - clips are used in filename order,
  same as `concat_edited.py`. If a bad take shouldn't be posted, delete or
  rename its `_edited.mp4` before the pipeline runs, or add its name to
  `posted_clips` in `posted_state.json` manually to skip it.
- Runs everything sequentially on your own PC/laptop's CPU - a big new
  batch of raw footage still takes a while to transcribe and encode before
  the post goes out.
