import sys
import os
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

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

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
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
                "Educational & harm reduction purposes only."
            ),
            "tags": [
                "trip report",
                "psychedelic experience",
                "erowid",
                "lsd",
                "dmt",
                "salvia",
                "cannabis"
            ],
            "categoryId": "22",  # People & Blogs
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
        print("Usage: python yt.py <video.mp4> [playlist_id]")
        sys.exit(1)

    video_file = sys.argv[1]
    playlist_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    base_name = os.path.basename(video_file)
    title = os.path.splitext(base_name)[0].replace("_", " ")


    upload_video(video_file, title, playlist_id)
