import json
import os
import subprocess
import requests
import tempfile
import shutil

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
# METNİ PARÇALA (TTS LIMIT)
# ---------------------------
def split_text(text, limit=450):
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
# MİRATTS VAR MI?
# ---------------------------
def miratts_available():
    return shutil.which("miratts") is not None

# ---------------------------
# MİRATTS İLE ÜRET
# ---------------------------
def generate_with_miratts(text_part, out_file):
    cmd = [
        "miratts",
        "--text", text_part,
        "--output", out_file,
        "--lang", "tr"
    ]
    subprocess.run(cmd, check=True)

# ---------------------------
# EDGE TTS İLE ÜRET
# ---------------------------
def generate_with_edge_tts(text_part, out_file):
    cmd = [
        "edge-tts",
        "--voice", "tr-TR-EmelNeural",
        "--text", text_part,
        "--write-media", out_file
    ]
    subprocess.run(cmd, check=True)

# ---------------------------
# PARÇA PARÇA SES ÜRET (MiraTTS -> Edge fallback)
# ---------------------------
use_miratts = miratts_available()

if use_miratts:
    print("🔥 MiraTTS bulundu, ana sistem MiraTTS!")
else:
    print("⚠️ MiraTTS yok, Edge-TTS fallback devrede.")

for i, part in enumerate(parts):
    out_file = os.path.join(tmp_dir, f"part_{i}.mp3")

    try:
        if use_miratts:
            generate_with_miratts(part, out_file)
        else:
            generate_with_edge_tts(part, out_file)

        audio_files.append(out_file)
        print(f"✅ Parça {i+1} üretildi")

    except Exception as e:
        print(f"❌ Parça {i+1} üretilemedi: {str(e)}")
        print("⚠️ Edge-TTS ile tekrar deneniyor...")

        try:
            generate_with_edge_tts(part, out_file)
            audio_files.append(out_file)
            print(f"✅ Parça {i+1} Edge-TTS ile üretildi")
        except Exception as e2:
            print(f"⛔ Parça {i+1} tamamen başarısız: {str(e2)}")
            raise SystemExit(1)

# ---------------------------
# MP3'LERİ FFMPEG İLE BİRLEŞTİR (DOĞRU YÖNTEM)
# ---------------------------
final_file = f"ses_{film_id}.mp3"
concat_list = os.path.join(tmp_dir, "concat.txt")

with open(concat_list, "w", encoding="utf-8") as f:
    for af in audio_files:
        f.write(f"file '{af}'\n")

print("🔗 FFmpeg ile sesler birleştiriliyor...")

cmd_concat = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", concat_list,
    "-c", "copy",
    final_file
]

subprocess.run(cmd_concat, check=True)

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
        timeout=180
    )

print("📡 Callback HTTP:", response.status_code)

# ---------------------------
# TEMİZLİK
# ---------------------------
try:
    shutil.rmtree(tmp_dir)
except:
    pass
