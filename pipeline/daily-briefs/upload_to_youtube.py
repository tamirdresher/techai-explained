"""
Upload TechAI daily brief videos to YouTube.
Uses YouTube Data API v3 with OAuth2 refresh token stored as env var.

IDENTITY: No personal names — channel = "TechAI Explained"
"""
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.http
from googleapiclient.errors import HttpError

# Playlist IDs (set these after creating playlists on YouTube)
PLAYLISTS = {
    "dotnet": os.environ.get("YT_PLAYLIST_DOTNET", ""),
    "ai": os.environ.get("YT_PLAYLIST_AI", ""),
    "cloud": os.environ.get("YT_PLAYLIST_CLOUD", ""),
    "dev": os.environ.get("YT_PLAYLIST_DEV", ""),
    "security": os.environ.get("YT_PLAYLIST_SECURITY", ""),
    "gamedev": os.environ.get("YT_PLAYLIST_GAMEDEV", ""),
}

TOPIC_TITLES = {
    "dotnet": ".NET Daily",
    "ai": "AI Daily",
    "cloud": "Cloud Daily",
    "dev": "Dev Daily",
    "security": "Security Brief",
    "gamedev": "GameDev Weekly",
}

RETRYABLE_STATUS_CODES = {429, 500, 503}
MAX_RETRIES = 5
BASE_RETRY_SECONDS = 30

# Quota-exceeded errors are non-fatal — video will be picked up on next scheduled run
QUOTA_REASONS = {"uploadLimitExceeded", "quotaExceeded", "rateLimitExceeded", "dailyLimitExceeded"}


def is_quota_error(exc: HttpError) -> bool:
    """Check if an HttpError is a YouTube quota/rate limit error.

    YouTube returns uploadLimitExceeded as HTTP 400 (not just 403),
    so we check the error reason regardless of status code.
    """
    if exc.resp.status in (400, 403, 429):
        try:
            import json
            detail = json.loads(exc.content.decode("utf-8"))
            errors = detail.get("error", {}).get("errors", [])
            return any(e.get("reason") in QUOTA_REASONS for e in errors)
        except Exception:
            pass
    return False


def check_credentials():
    """Verify required YouTube OAuth env vars are set. Exit(0) with clear message if not."""
    required = ["YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(
            "⚠️ YouTube credentials not configured. "
            "Set YOUTUBE_REFRESH_TOKEN, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET secrets. "
            "See issue #67."
        )
        sys.exit(0)


def get_youtube_client():
    """Build authenticated YouTube client from stored refresh token."""
    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
    )
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def upload_video(youtube, video_path: Path, topic: str, date_str: str, language: str = "en"):
    """Upload a single video to YouTube with exponential backoff on transient errors.

    Returns:
        video_id on success, "quota_exceeded" if quota hit, raises on other errors.
    """
    lang_suffix = " (Hebrew)" if language == "he" else ""
    title_topic = TOPIC_TITLES.get(topic, topic.upper())
    title = f"{title_topic}{lang_suffix} — {date_str}"

    description = (
        f"Daily tech brief: {title_topic} for {date_str}.\n\n"
        f"TechAI Explained — cutting through the noise, every day.\n\n"
        f"#TechAI #{topic} #tech #programming"
    )

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["tech", "programming", topic, "daily brief", "TechAI"],
            "categoryId": "28",  # Science & Technology
            "defaultLanguage": language,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = googleapiclient.http.MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5,  # 5 MB chunks
    )

    print(f"  Uploading: {video_path.name} → '{title}'")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"    Progress: {int(status.progress() * 100)}%")

            video_id = response["id"]
            video_url = f"https://youtu.be/{video_id}"
            print(f"  ✅ Uploaded: {video_url}")

            # Add to playlist if configured
            playlist_id = PLAYLISTS.get(topic)
            if playlist_id:
                try:
                    youtube.playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": playlist_id,
                                "resourceId": {"kind": "youtube#video", "videoId": video_id},
                            }
                        },
                    ).execute()
                    print(f"  📋 Added to playlist: {topic}")
                except HttpError as pe:
                    print(f"  ⚠️ Playlist add failed (non-fatal): {pe}")

            return video_id

        except HttpError as e:
            # Quota exceeded — stop retrying, mark for next run
            if is_quota_error(e):
                print(f"  ⏳ Quota exceeded for {video_path.name} �� will retry next scheduled run")
                return "quota_exceeded"

            # Transient server errors — exponential backoff
            if e.resp.status in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                backoff = BASE_RETRY_SECONDS * (2 ** (attempt - 1))
                print(
                    f"  ⚠️ Transient error (HTTP {e.resp.status}) on attempt {attempt}/{MAX_RETRIES}. "
                    f"Retrying in {backoff}s..."
                )
                time.sleep(backoff)
                media = googleapiclient.http.MediaFileUpload(
                    str(video_path),
                    mimetype="video/mp4",
                    resumable=True,
                    chunksize=1024 * 1024 * 5,
                )
            else:
                raise


def main():
    check_credentials()

    parser = argparse.ArgumentParser(description="Upload TechAI daily briefs to YouTube")
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Date to upload (YYYY-MM-DD)",
    )
    parser.add_argument("--topic", help="Specific topic to upload (default: all)")
    parser.add_argument(
        "--language", default="both", choices=["en", "he", "both"]
    )
    parser.add_argument(
        "--search-dir",
        dest="search_dir",
        default=None,
        help="Root dir to search for brief MP4s (used when artifact names vary)",
    )
    parser.add_argument(
        "--max-uploads",
        dest="max_uploads",
        type=int,
        default=6,
        help="Maximum number of videos to upload in this run (default: 6)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=60,
        help="Seconds to wait between uploads to avoid rate limits (default: 60)",
    )
    args = parser.parse_args()

    default_dir = Path(__file__).parent / "output" / args.date
    if default_dir.exists():
        output_dir = default_dir
    elif args.search_dir:
        import shutil
        search_root = Path(args.search_dir)
        output_dir = default_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        for mp4 in search_root.rglob("*.mp4"):
            dest = output_dir / mp4.name
            if not dest.exists():
                shutil.copy2(mp4, dest)
                print(f"  �� Collected {mp4.name} from {mp4.parent.name}/")
        if not any(output_dir.iterdir()):
            print(f"⚠️ No MP4 files found under {search_root} — skipping upload.")
            sys.exit(0)
    else:
        print(f"⚠️ No output directory for {args.date}: {default_dir} — skipping upload.")
        sys.exit(0)

    youtube = get_youtube_client()
    topics = (
        [args.topic]
        if args.topic
        else ["dotnet", "ai", "cloud", "dev", "security", "gamedev"]
    )
    date_display = datetime.strptime(args.date, "%Y-%m-%d").strftime("%B %d, %Y")

    uploaded = 0
    skipped = 0
    failed = 0
    quota_deferred = 0
    quota_hit = False

    for topic in topics:
        for lang, suffix in [("en", "-brief.mp4"), ("he", "-he-brief.mp4")]:
            if args.language not in (lang, "both"):
                continue

            video_path = output_dir / f"{topic}{suffix}"
            if not video_path.exists():
                skipped += 1
                continue

            # Respect upload cap
            if uploaded >= args.max_uploads:
                print(f"  ⏸️ Upload cap ({args.max_uploads}) reached — deferring {video_path.name}")
                quota_deferred += 1
                continue

            # If we already hit quota, don't attempt more uploads
            if quota_hit:
                print(f"  ⏳ Quota already exceeded — deferring {video_path.name} to next run")
                quota_deferred += 1
                continue

            try:
                result = upload_video(youtube, video_path, topic, date_display, lang)
                if result == "quota_exceeded":
                    quota_deferred += 1
                    quota_hit = True
                else:
                    uploaded += 1
                    # Delay between uploads to stay under rate limits
                    if args.delay > 0:
                        print(f"  ⏱️ Waiting {args.delay}s before next upload...")
                        time.sleep(args.delay)
            except Exception as exc:
                print(f"  ❌ Failed to upload {video_path.name}: {exc}")
                failed += 1

    print(f"\n📊 Results: �� {uploaded} uploaded | ⏭️ {skipped} skipped | "
          f"⏳ {quota_deferred} deferred | ❌ {failed} failed")

    if quota_deferred > 0:
        print(f"ℹ️  {quota_deferred} video(s) deferred due to quota — will upload on next scheduled run.")

    # Exit 0 even if quota was hit — this is expected for new channels.
    # Only hard-fail if there were non-quota errors AND zero successful uploads.
    if failed > 0 and uploaded == 0 and quota_deferred == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
