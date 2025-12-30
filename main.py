import subprocess
import logging
import sys
import os
from dotenv import load_dotenv
import argparse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

AUDIO_SCRIPT = "audio.py"
GEMINI_AUDIO_SCRIPT = "audio_gemini.py"
VIDEO_SCRIPT = "video.py"
YT_SCRIPT = "yt.py"

# -------------------------
# Argument parsing
# -------------------------
parser = argparse.ArgumentParser(description="Run Lysergic Podcast pipeline")
parser.add_argument("experience_url", nargs="?", help="URL or path of the experience")
parser.add_argument("-y", "--yes", action="store_true", help="Auto-upload to YouTube")
parser.add_argument("-g", "--gemini", action="store_true", help="Use Gemini audio script")

args = parser.parse_args()

experience_url = args.experience_url
auto_upload = args.yes
use_gemini = args.gemini

logger.info("experience_url=%s, auto_upload=%s, use_gemini=%s",
            experience_url, auto_upload, use_gemini)

# -------------------------
# Choose audio script
# -------------------------
audio_script = GEMINI_AUDIO_SCRIPT if use_gemini else AUDIO_SCRIPT
logger.info("Running %s...", audio_script)

cmd = ["python", audio_script]
if experience_url:
    cmd.append(experience_url)

# -------------------------
# Run audio script
# -------------------------
try:
    result = subprocess.run(
        cmd,
        check=True,
        text=True,
        stdout=subprocess.PIPE
    )
except subprocess.CalledProcessError:
    logger.error("%s failed!", audio_script)
    sys.exit(1)

# -------------------------
# Parse audio.py output
# Expected:
# audio.wav | subtitle.srt | primary_substance | experience_url
# -------------------------
output_line = result.stdout.strip().splitlines()[-1]
parts = [p.strip() for p in output_line.split("|")]

if len(parts) not in (3, 4):
    logger.error("Unexpected audio.py output: %s", output_line)
    sys.exit(1)

audio_file = parts[0]
subtitle_file = parts[1]
primary_substance = parts[2]
frontend_experience_url = parts[3] if len(parts) == 4 else None

logger.info("Generated audio: %s", audio_file)
logger.info("Generated subtitles: %s", subtitle_file)
logger.info("Primary substance: %s", primary_substance)

if frontend_experience_url:
    logger.info("Experience URL: %s", frontend_experience_url)

# -------------------------
# Run video.py
# -------------------------
logger.info("Running video.py...")
try:
    result = subprocess.run(
        ["python", VIDEO_SCRIPT, audio_file],
        check=True,
        text=True,
        stdout=subprocess.PIPE
    )
except subprocess.CalledProcessError:
    logger.error("video.py failed!")
    sys.exit(1)

video_file = result.stdout.strip().splitlines()[-1]
logger.info("Generated video: %s", video_file)

# -------------------------
# Upload to YouTube
# -------------------------
logger.info("Preparing to upload to YouTube...")
PLAYLIST_ID = os.getenv("YT_PLAYLIST_ID")

if not auto_upload:
    answer = input("Upload video to YouTube? [y/n]: ").strip().lower()
    if answer != "y":
        logger.info("Upload cancelled.")
        sys.exit(0)

logger.info("Uploading to YouTube...")
yt_cmd = [
    "python",
    YT_SCRIPT,
    video_file,
    PLAYLIST_ID,
    primary_substance,
]

if frontend_experience_url:
    yt_cmd.append(frontend_experience_url)

try:
    subprocess.run(yt_cmd, check=True)
except subprocess.CalledProcessError:
    logger.error("YouTube upload failed!")
    sys.exit(1)

logger.info("YouTube upload completed!")
logger.info("Pipeline completed successfully!")
