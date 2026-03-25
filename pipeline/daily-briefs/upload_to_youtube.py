"""
Upload TechAI daily brief videos to YouTube.
Uses YouTube Data API v3 with OAuth2 refresh token stored as env var.

IDENTITY: No personal names — channel = "TechAI Explained"
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.http

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
    """Upload a single video to YouTube."""
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
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    Progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"  ✅ Uploaded: https://youtu.be/{video_id}")

    # Add to playlist if configured
    playlist_id = PLAYLISTS.get(topic)
    if playlist_id:
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

    return video_id


def main():
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
    args = parser.parse_args()

    output_dir = Path(__file__).parent / "output" / args.date
    if not output_dir.exists():
        print(f"❌ No output directory for {args.date}: {output_dir}")
        sys.exit(1)

    youtube = get_youtube_client()
    topics = (
        [args.topic]
        if args.topic
        else ["dotnet", "ai", "cloud", "dev", "security", "gamedev"]
    )
    date_display = datetime.strptime(args.date, "%Y-%m-%d").strftime("%B %d, %Y")

    uploaded = 0
    for topic in topics:
        if args.language in ("en", "both"):
            en_path = output_dir / f"{topic}-brief.mp4"
            if en_path.exists():
                upload_video(youtube, en_path, topic, date_display, "en")
                uploaded += 1

        if args.language in ("he", "both"):
            he_path = output_dir / f"{topic}-he-brief.mp4"
            if he_path.exists():
                upload_video(youtube, he_path, topic, date_display, "he")
                uploaded += 1

    print(f"\n✅ Done. Uploaded {uploaded} videos for {args.date}.")


if __name__ == "__main__":
    main()
