import json
import os
import requests
import subprocess

# GitHub event payload dosyası
event_path = os.environ.get("GITHUB_EVENT_PATH")

with open(event_path, "r", encoding="utf-8") as f:
    event = json.load(f)

payload = event["client_payload"]

film_id  = payload["film_id"]
text     = payload["text"]
callback = payload["callback"]

output_file = f"ses_{film_id}.mp3"

print("🎬 Film ID:", film_id)
print("🔊 Ses üretiliyor...")

# Edge TTS komutu
cmd = [
    "edge-tts",
    "--voice", "tr-TR-AhmetNeural",
    "--text", text,
    "--write-media", output_file
]

subprocess.run(cmd, check=True)

print("✅ Ses üretildi:", output_file)

# Sunucuya geri gönder
print("📤 Sunucuya gönderiliyor...")

with open(output_file, "rb") as audio:
    response = requests.post(
        callback,
        files={"audio": audio},
        data={"film_id": film_id},
        timeout=60
    )

print("📡 Sunucu cevabı:", response.status_code)
