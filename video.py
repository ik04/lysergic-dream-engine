import sys
import os
import logging
import random
import subprocess
import re

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeAudioClip,
)
from moviepy.audio.fx.all import volumex, audio_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------
# Args
# -------------------------
if len(sys.argv) < 2:
    logger.error("Usage: python video.py <tts_audio_file>")
    sys.exit(1)

tts_audio_file = sys.argv[1]
base_name = os.path.splitext(os.path.basename(tts_audio_file))[0]

subtitle_file = f"{base_name}.srt"

random_music_index = random.randint(1, 7)
random_clip_index = random.randint(1, 5)

music_file = f"music/{random_music_index}.mp3"
clip_file = f"clips/{random_clip_index}.mp4"

output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

temp_video = os.path.join(output_folder, f"{base_name}_nosubs.mp4")
output_file = os.path.join(output_folder, f"{base_name}.mp4")

# -------------------------
# Clean SRT (punctuation + spacing only)
# -------------------------
def clean_srt(path: str):
    logger.info("Cleaning subtitles: %s", path)

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    cleaned = []
    for line in lines:
        stripped = line.strip()

        # Keep indices
        if stripped.isdigit():
            cleaned.append(line)
            continue

        # Keep timestamps
        if "-->" in line:
            cleaned.append(line)
            continue

        # Preserve blank lines
        if not stripped:
            cleaned.append("\n")
            continue

        text = stripped

        # Fix spacing around punctuation only
        text = re.sub(r"\s+([,.!?])", r"\1", text)
        text = re.sub(r"([,.!?])([A-Za-z])", r"\1 \2", text)
        text = re.sub(r"\s+", " ", text)

        cleaned.append(text + "\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(cleaned)

# -------------------------
# Load clips
# -------------------------
logger.info("Loading TTS audio: %s", tts_audio_file)
tts_clip = AudioFileClip(tts_audio_file)

logger.info("Loading background music: %s", music_file)
music_clip = AudioFileClip(music_file)

logger.info("Loading video clip: %s", clip_file)
video_clip = VideoFileClip(clip_file)

# -------------------------
# Loop video to match TTS
# -------------------------
loops = int(tts_clip.duration // video_clip.duration) + 1
video_clip = video_clip.loop(n=loops).subclip(0, tts_clip.duration)

# -------------------------
# Loop + mix music
# -------------------------
music_clip = audio_loop(music_clip, duration=tts_clip.duration)
music_clip = volumex(music_clip, 0.05)

combined_audio = CompositeAudioClip([music_clip, tts_clip])
video_clip = video_clip.set_audio(combined_audio)

# -------------------------
# Export without subtitles
# -------------------------
logger.info("Rendering base video (no subtitles)")
video_clip.write_videofile(
    temp_video,
    codec="libx264",
    audio_codec="aac",
    preset="medium",
    threads=4,
)

video_clip.close()
tts_clip.close()
music_clip.close()

# -------------------------
# Burn subtitles with FFmpeg
# -------------------------
if os.path.exists(subtitle_file):
    clean_srt(subtitle_file)

    logger.info("Burning subtitles from %s", subtitle_file)

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", temp_video,
        "-vf", f"subtitles={subtitle_file}",
        "-c:a", "copy",
        output_file,
    ]

    subprocess.run(ffmpeg_cmd, check=True)

    os.remove(temp_video)
    os.remove(subtitle_file)
    logger.info("Removed subtitle file: %s", subtitle_file)

else:
    logger.warning("No subtitles found, skipping burn-in")
    os.rename(temp_video, output_file)

# -------------------------
# Cleanup
# -------------------------
if os.path.exists(tts_audio_file):
    os.remove(tts_audio_file)
    logger.info("Removed temporary audio file: %s", tts_audio_file)

logger.info("Final video ready: %s", output_file)

print(output_file)
