import sys
import os
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS = "client_secret.json"
TOKEN_FILE = "youtube_token.json"


def get_youtube():
    creds = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        logger.info("Refreshing YouTube access token")
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    # Full re-auth only if needed
    if not creds or not creds.valid:
        logger.info("Starting browser authentication flow")
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS, SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(video_path, title, playlist_id=None):
    youtube = get_youtube()

    body = {
        "snippet": {
            "title": title,
            "description": (
                "Narrated psychoactive experience report.\n\n"
                "Source: Erowid.org\n"
                "Educational & harm reduction purposes only.\n\n"
                "Generated using The Lysergic Dream Engine:\n"
                "https://github.com/ik04/lysergic-dream-engine\n\n"
                "Explore more experiences:\n"
                "https://lysergic.vercel.app/"
            ),
            "tags": [
                "trip report",
                "psychedelic experience",
                "erowid",
                "lsd",
                "dmt",
                "salvia",
                "cannabis",
                "mdma"
            ],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        video_path,
        chunksize=-1,
        resumable=True,
        mimetype="video/*"
    )

    logger.info("Uploading video to YouTube...")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = request.execute()
    video_id = response["id"]

    logger.info("Uploaded video ID: %s", video_id)

    if playlist_id:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    }
                }
            }
        ).execute()

        logger.info("Added video to playlist: %s", playlist_id)

    return video_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python yt.py <video.mp4> [playlist_id] [substance]")
        sys.exit(1)

    video_file = sys.argv[1]
    playlist_id = sys.argv[2] if len(sys.argv) > 2 else None
    substance = sys.argv[3] if len(sys.argv) > 3 else None

    base_name = os.path.basename(video_file)
    base_title = os.path.splitext(base_name)[0].replace("_", " ")

    if substance:
        title = f"{base_title} [{substance} Trip Report]"
    else:
        title = base_title

    upload_video(video_file, title, playlist_id)
