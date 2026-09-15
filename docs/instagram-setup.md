# Instagram (Meta Graph API) setup for @kissa_suzu123

Record of the one-time setup done to allow posting Reels to
`@kissa_suzu123` via `tools/instagram_publish/`. None of the values below
are secrets (App ID and object IDs are not sensitive by themselves) - the
App Secret and any access token are secrets and are intentionally not
recorded here or anywhere in this repo.

## What was set up

1. `@kissa_suzu123` converted to a Professional (Business) Instagram account.
2. A new Facebook Page, **喫茶すず**, created (Page ID `1289181057621862`)
   and linked to the Instagram account.
3. A Meta developer app, **kissa_suzu123 bot** (App ID `1666421484474977`),
   created with the Instagram Graph API product added (Facebook Login for
   Business route, since the Instagram account is linked via a Page).
4. Under [facebook.com/settings?tab=business_tools](https://www.facebook.com/settings?tab=business_tools) →
   kissa_suzu123 bot → manage access, both the **喫茶すず** Page and the
   `kissa_suzu123` Instagram account are granted.
5. **Instagram Business Account ID: `17841478716095901`** — this is the ID
   `tools/instagram_publish/` scripts need as `--ig-user-id` /
   `-IgUserId`.

## Known quirk

`GET /me/accounts` did not list the 喫茶すず page even after granting
access through every UI path (Graph API Explorer's page picker, and the
Business Integrations settings page) - it kept returning an empty list.
Querying the page directly by its known ID worked fine and returned a
valid page-scoped access token:

```
GET /v25.0/1289181057621862?fields=name,access_token,instagram_business_account&access_token=<user token>
```

If `/me/accounts` is empty again in the future (e.g. after re-doing this
setup for a different page), don't assume access wasn't granted - try
querying the specific page ID directly first.

## Regenerating the page access token (needed every ~60 days)

1. https://developers.facebook.com/tools/explorer/ → select **kissa_suzu123 bot**
2. Get Token → Get User Access Token → permissions: `instagram_basic`,
   `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`
   → Generate Access Token
3. Exchange for a long-lived user token:
   `GET /oauth/access_token?grant_type=fb_exchange_token&client_id=1666421484474977&client_secret=<app secret>&fb_exchange_token=<short token>`
4. Get the page-scoped token from the long-lived user token:
   `GET /1289181057621862?fields=name,access_token&access_token=<long-lived user token>`
5. Use that page-scoped `access_token` as `-PageToken` / `--page-token` in
   `tools/instagram_publish/`.

The App Secret lives only in the Meta app dashboard (Settings → Basic) -
never commit it or paste it anywhere outside that one-off exchange step.
