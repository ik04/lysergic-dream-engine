import requests
from dotenv import load_dotenv
from TTS.api import TTS
import soundfile as sf
import numpy as np
import re
import logging
import string
import sys
from urllib.parse import unquote
from collections import Counter

# -------------------------
# Logging setup
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

# -------------------------
# Helpers
# -------------------------
def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def silence(seconds: float, sr: int):
    return np.zeros(int(seconds * sr), dtype=np.float32)

def sanitize_filename(name: str) -> str:
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return "".join(c for c in name if c in valid_chars).replace(" ", "_")

def split_with_punctuation(text: str):
    """
    Returns list of (text, pause_seconds)
    """
    parts = re.findall(r'[^.,!?;:]+[.,!?;:]?', text)
    result = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        last_char = part[-1]
        if last_char in ".!?":
            pause = 1.0
        elif last_char in ",;:":
            pause = 0.3
        else:
            pause = 0.3

        result.append((part, pause))

    return result

# -------------------------
# Substance frequency detection
# -------------------------
SUBSTANCES = [
    "LSD",
    "DMT",
    "Salvia",
    "MDMA",
    "Cannabis",
    "Heroin",
]

def detect_primary_substance(text: str) -> str:
    text_lower = text.lower()
    counts = Counter()

    for substance in SUBSTANCES:
        pattern = rf"\b{substance.lower()}\b"
        matches = re.findall(pattern, text_lower)
        if matches:
            counts[substance] += len(matches)

    if not counts:
        return "Unknown"

    primary, _ = counts.most_common(1)[0]
    logger.info("Substance frequency: %s", dict(counts))
    return primary

# -------------------------
# Check for URL argument
# -------------------------
experience_url = None
if len(sys.argv) > 1:
    experience_url = unquote(sys.argv[1])
    logger.info("Using provided experience URL: %s", experience_url)

# -------------------------
# Fetch random experience if no URL
# -------------------------
if not experience_url:
    logger.info("Fetching random Erowid experience")
    url = "https://lysergic.kaizenklass.xyz/api/v1/erowid/random/experience?size_per_substance=1"
    substances = {
        "urls": [
            "https://www.erowid.org/chemicals/dmt/dmt.shtml",
            "https://www.erowid.org/chemicals/lsd/lsd.shtml",
            "https://www.erowid.org/plants/salvia/salvia.shtml",
            "https://www.erowid.org/plants/cannabis/cannabis.shtml",
            "https://www.erowid.org/chemicals/mdma/mdma.shtml",
            "https://www.erowid.org/chemicals/heroin/heroin.shtml",
        ]
    }
    experience = requests.post(url, json=substances).json()
    experience_url = experience["experience"]["url"]

# -------------------------
# Fetch experience details
# -------------------------
logger.info("Fetching full experience details")
resp = requests.post(
    "https://lysergic.kaizenklass.xyz/api/v1/erowid/experience",
    json={"url": experience_url}
)
data = resp.json()["data"]

clean_experience = {
    "title": data["title"],
    "username": data["author"],
    "gender": data["metadata"].get("gender", "Unknown"),
    "age": data["metadata"].get("age", "Unknown"),
    "content": data["content"],
    "doses": data.get("doses", []),
}

logger.info(
    "Loaded experience: '%s' by %s",
    clean_experience["title"],
    clean_experience["username"],
)

# -------------------------
# Detect primary substance (with fallback)
# -------------------------
primary_substance = detect_primary_substance(clean_experience["content"])

if primary_substance == "Unknown" and clean_experience["doses"]:
    primary_substance = clean_experience["doses"][0]["substance"]
    logger.info("Frequency detection failed, fallback to dose metadata")

logger.info("Primary substance detected: %s", primary_substance)

# -------------------------
# Build narration script
# -------------------------
tts_script = f"""
Welcome.

This is a narrated experience report sourced from Erowid dot org,
generated using The Lysergic Dream Engine.

This video is not an endorsement, not medical advice,
and does not encourage illegal activity.

Listener discretion is advised.

{clean_experience['title']}.

{("an" if primary_substance in ["LSD", "MDMA"] else "a")} {primary_substance} Trip Report.

This experience was submitted under the username
{clean_experience['username']}.

Reported age: {clean_experience['age']},
Reported gender: {clean_experience['gender']}.

{clean_experience['content']}

I hope you found this experience report informative and enjoyable.

Thank you for listening.
"""

clean_text = normalize_text(tts_script)
segments = split_with_punctuation(clean_text)

# -------------------------
# Load TTS
# -------------------------
logger.info("Loading Coqui TTS model")
tts = TTS(
    model_name="tts_models/en/vctk/vits",
    progress_bar=False,
    gpu=False
)

speaker = "p232"
sr = tts.synthesizer.output_sample_rate

# -------------------------
# Generate audio (DEDUP UPGRADE)
# -------------------------
audio_parts = []
last_spoken = None  # <-- upgrade

for text, pause in segments:
    normalized = normalize_text(text).lower()

    # Skip consecutive duplicate chunks
    if normalized == last_spoken:
        logger.warning("Skipping duplicate segment: %s", text[:60])
        continue

    last_spoken = normalized

    logger.info("Speaking: %s", text[:60])
    wav = tts.tts(text=text, speaker=speaker)
    audio_parts.append(wav)
    audio_parts.append(silence(pause, sr))

final_audio = np.concatenate(audio_parts)

# -------------------------
# Save
# -------------------------
audio_filename = sanitize_filename(clean_experience["title"]) + ".wav"
sf.write(audio_filename, final_audio, sr)
logger.info("Saved audio as %s", audio_filename)

# -------------------------
# Output for pipeline
# -------------------------
print(f"{audio_filename}|{primary_substance}")
