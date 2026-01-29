import json, os, requests, subprocess

event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
p = event["client_payload"]

film_id  = p["film_id"]
film_adi = p["film_adi"]
ses_url  = p["ses_url"]
callback = p["callback"]

print("🎬 Film:", film_adi)

# ======================
# MP3 indir
# ======================
mp3 = f"ses_{film_id}.mp3"

r = requests.get(ses_url, timeout=30)
r.raise_for_status()

with open(mp3, "wb") as f:
    f.write(r.content)

# ======================
# Süre hesapla
# ======================
duration = subprocess.check_output([
    "ffprobe", "-i", mp3,
    "-show_entries", "format=duration",
    "-v", "quiet", "-of", "csv=p=0"
]).decode().strip()

duration = int(float(duration)) + 10
print("⏱ Süre:", duration)

# ======================
# YouTube fragman indir
# ======================
subprocess.run([
    "yt-dlp",
    "-f", "bv*[ext=mp4]/bv*",
    "--no-audio",
    "-o", "video.mp4",
    f"ytsearch1:{film_adi} fragman"
], check=True)

# ======================
# Kes + Ses bindir
# ======================
subprocess.run([
    "ffmpeg", "-y",
    "-i", "video.mp4",
    "-i", mp3,
    "-t", str(duration),
    "-shortest",
    "-c:v", "copy",
    "fragman.mp4"
], check=True)

# ======================
# Callback
# ======================
requests.post(
    callback,
    files={"video": open("fragman.mp4", "rb")},
    data={"film_id": film_id},
    timeout=60
)

print("✅ Fragman gönderildi")

# ======================
# Temizlik
# ======================
for f in [mp3, "video.mp4", "fragman.mp4"]:
    if os.path.exists(f):
        os.remove(f)
