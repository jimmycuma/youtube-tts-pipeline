import json
import os
import subprocess
import requests
import tempfile

# ---------------------------
# GITHUB EVENT
# ---------------------------
event_path = os.environ.get("GITHUB_EVENT_PATH")

with open(event_path, "r", encoding="utf-8") as f:
    event = json.load(f)

payload  = event["client_payload"]
film_id  = payload["film_id"]
text     = payload["text"]
callback = payload["callback"]

print("🎬 Film ID:", film_id)

# ---------------------------
# METNİ PARÇALA (EDGE TTS LIMIT)
# ---------------------------
def split_text(text, limit=500):
    parts = []
    current = ""

    for sentence in text.split("."):
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current) + len(sentence) < limit:
            current += sentence + ". "
        else:
            parts.append(current.strip())
            current = sentence + ". "

    if current:
        parts.append(current.strip())

    return parts

parts = split_text(text)

print(f"🔊 Parça sayısı: {len(parts)}")

# ---------------------------
# GEÇİCİ KLASÖR
# ---------------------------
tmp_dir = tempfile.mkdtemp()
audio_files = []

# ---------------------------
# PARÇA PARÇA SES ÜRET
# ---------------------------
for i, part in enumerate(parts):
    out_file = os.path.join(tmp_dir, f"part_{i}.mp3")

    cmd = [
        "edge-tts",
        "--voice", "tr-TR-AhmetNeural",
        "--text", part,
        "--write-media", out_file
    ]

    subprocess.run(cmd, check=True)
    audio_files.append(out_file)

    print(f"✅ Parça {i+1} üretildi")

# ---------------------------
# MP3'LERİ BİRLEŞTİR (FFMPEG YOK → BINARY CONCAT)
# ---------------------------
final_file = f"ses_{film_id}.mp3"

with open(final_file, "ab") as final:
    for af in audio_files:
        with open(af, "rb") as f:
            final.write(f.read())

print("🎧 Final ses oluşturuldu:", final_file)

# ---------------------------
# SUNUCUYA GERİ GÖNDER
# ---------------------------
print("📤 Sunucuya gönderiliyor...")

with open(final_file, "rb") as audio:
    response = requests.post(
        callback,
        files={"audio": audio},
        data={"film_id": film_id},
        timeout=120
    )

print("📡 Callback HTTP:", response.status_code)
