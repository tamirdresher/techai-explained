"""
One-time setup: Get YouTube OAuth refresh token.
Run locally: python setup_youtube_auth.py

Copy the three values printed to GitHub repo secrets:
  YOUTUBE_REFRESH_TOKEN, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET
"""
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    # Requires client_secrets.json from Google Cloud Console.
    # Download from: APIs & Services → Credentials → OAuth 2.0 Client → Download JSON
    # then rename the file to client_secrets.json before running this script.
    if not os.path.exists("client_secrets.json"):
        print("❌ client_secrets.json not found.")
        print("Download from Google Cloud Console → APIs & Services → Credentials")
        print("Rename the downloaded file to client_secrets.json and run again.")
        return

    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n✅ Authentication successful!")
    print("\nAdd these to your GitHub repo secrets:")
    print(f"  YOUTUBE_REFRESH_TOKEN = {creds.refresh_token}")
    print(f"  YOUTUBE_CLIENT_ID     = {creds.client_id}")
    print(f"  YOUTUBE_CLIENT_SECRET = {creds.client_secret}")


if __name__ == "__main__":
    main()
