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
        "--voice", "tr-TR-EmelNeural",
        "--text", part,
        "--write-media", out_file
    ]

    subprocess.run(cmd, check=True)
    audio_files.append(out_file)

    print(f"✅ Parça {i+1} üretildi")

# ---------------------------
# MP3 CONCAT LIST (FFMPEG)
# ---------------------------
concat_file = os.path.join(tmp_dir, "concat.txt")

with open(concat_file, "w", encoding="utf-8") as f:
    for af in audio_files:
        f.write(f"file '{af}'\n")

raw_audio = f"raw_{film_id}.mp3"
final_audio = f"ses_{film_id}.mp3"

print("🔗 Parçalar birleştiriliyor...")

subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", concat_file,
    "-c", "copy",
    raw_audio
], check=True)

print("✅ Ham ses birleştirildi:", raw_audio)

# ---------------------------
# MASTERING (DUYGULU SES EFEKTİ)
# ---------------------------
print("🎚️ Mastering uygulanıyor (EQ + Compressor + Reverb + Normalize)...")

ffmpeg_filter = (
    "equalizer=f=120:t=q:w=1:g=4,"     # bass boost
    "equalizer=f=3000:t=q:w=1:g=2,"    # clarity boost
    "acompressor=threshold=-18dB:ratio=3:attack=20:release=250,"
    "alimiter=limit=0.9,"
    "aecho=0.8:0.88:60:0.25,"          # reverb/echo vibe
    "loudnorm=I=-14:TP=-1.5:LRA=11"    # youtube standard
)

subprocess.run([
    "ffmpeg", "-y",
    "-i", raw_audio,
    "-af", ffmpeg_filter,
    "-b:a", "192k",
    final_audio
], check=True)

print("🎧 Final mastering ses oluşturuldu:", final_audio)

# ---------------------------
# SUNUCUYA GERİ GÖNDER
# ---------------------------
print("📤 Sunucuya gönderiliyor...")

with open(final_audio, "rb") as audio:
    response = requests.post(
        callback,
        files={"audio": audio},
        data={"film_id": film_id},
        timeout=120
    )

print("📡 Callback HTTP:", response.status_code)
print("✅ İşlem tamamlandı.")
