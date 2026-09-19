# Publish a video as an Instagram Reel via the Meta Graph API.
#
# Must be run from a machine with normal internet access (this repo's dev
# sandbox cannot reach graph.facebook.com due to its network policy).
#
# The video must already be at a public HTTPS URL (Instagram's servers
# fetch it from there) - e.g. uploaded to Supabase Storage, or any other
# public host. This script does not upload the video itself.
#
# Usage:
#   .\publish_reel.ps1 -PageToken "<page access token>" -IgUserId "17841478716095901" -VideoUrl "https://.../video.mp4" -Caption "投稿文 #ハッシュタグ"
#
# The page token and IG user ID were obtained during the one-time Meta app
# setup (see docs/instagram-setup.md). The page token is long-lived
# (~60 days); regenerate it via the same Graph API Explorer flow once it
# expires.

param(
    [Parameter(Mandatory=$true)][string]$PageToken,
    [Parameter(Mandatory=$true)][string]$IgUserId,
    [Parameter(Mandatory=$true)][string]$VideoUrl,
    [Parameter(Mandatory=$true)][string]$Caption,
    [string]$ApiVersion = "v25.0",
    [int]$PollIntervalSeconds = 5,
    [int]$MaxPollAttempts = 60
)

$ErrorActionPreference = "Stop"

Write-Host "1/3: Creating media container..."
$createUri = "https://graph.facebook.com/$ApiVersion/$IgUserId/media"
$createBody = @{
    media_type   = "REELS"
    video_url    = $VideoUrl
    caption      = $Caption
    access_token = $PageToken
}
$container = Invoke-RestMethod -Uri $createUri -Method Post -Body $createBody
$creationId = $container.id
Write-Host "   container id: $creationId"

Write-Host "2/3: Waiting for Instagram to finish processing the video..."
$statusUri = "https://graph.facebook.com/$ApiVersion/$creationId`?fields=status_code,status&access_token=$PageToken"
$attempt = 0
do {
    Start-Sleep -Seconds $PollIntervalSeconds
    $attempt++
    $status = Invoke-RestMethod -Uri $statusUri
    Write-Host "   [$attempt/$MaxPollAttempts] status: $($status.status_code)"
    if ($status.status_code -eq "ERROR") {
        Write-Error "Instagram failed to process the video: $($status.status)"
        exit 1
    }
} while ($status.status_code -ne "FINISHED" -and $attempt -lt $MaxPollAttempts)

if ($status.status_code -ne "FINISHED") {
    Write-Error "Timed out waiting for processing to finish (last status: $($status.status_code))"
    exit 1
}

Write-Host "3/3: Publishing..."
$publishUri = "https://graph.facebook.com/$ApiVersion/$IgUserId/media_publish"
$publishBody = @{
    creation_id  = $creationId
    access_token = $PageToken
}
$result = Invoke-RestMethod -Uri $publishUri -Method Post -Body $publishBody

Write-Host ""
Write-Host "Published. Media ID: $($result.id)"
Write-Host "https://www.instagram.com/p/$($result.id)/ (or check the profile directly - shortcode isn't returned by this call)"
