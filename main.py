import subprocess
import logging
import sys
from dotenv import load_dotenv
import os

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
# Parse arguments
# -------------------------
experience_url = None
auto_upload = False
use_gemini = False

for arg in sys.argv[1:]:
    if arg == "-y":
        auto_upload = True
    elif arg == "-g":
        use_gemini = True
    else:
        experience_url = arg

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
    result = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE)
except subprocess.CalledProcessError:
    logger.error("%s failed!", audio_script)
    sys.exit(1)

output = result.stdout.strip().splitlines()[-1]
audio_file, primary_substance = output.split("|", 1)

logger.info("Generated audio: %s", audio_file)
logger.info("Primary substance: %s", primary_substance)

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
subprocess.run(
    ["python", YT_SCRIPT, video_file, PLAYLIST_ID, primary_substance],
    check=True
)

logger.info("YouTube upload completed!")
logger.info("Pipeline completed successfully!")
