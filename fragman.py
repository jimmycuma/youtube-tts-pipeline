import json, os, requests, subprocess

event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
p = event["client_payload"]

film_id = p["film_id"]
film_adi = p["film_adi"]
ses_url = p["ses_url"]
callback = p["callback"]

print("🎬 Film:", film_adi)

# MP3 indir
mp3 = f"ses_{film_id}.mp3"
open(mp3, "wb").write(requests.get(ses_url).content)

# Süre
duration = subprocess.check_output([
    "ffprobe", "-i", mp3,
    "-show_entries", "format=duration",
    "-v", "quiet", "-of", "csv=p=0"
]).decode().strip()

duration = int(float(duration)) + 10

# YouTube fragman indir
subprocess.run([
    "yt-dlp",
    "-f", "bestvideo",
    "--no-audio",
    "-o", "video.mp4",
    f"ytsearch1:{film_adi} fragman"
], check=True)

# Kes + Sesle birleştir
subprocess.run([
    "ffmpeg", "-y",
    "-i", "video.mp4",
    "-i", mp3,
    "-t", str(duration),
    "-shortest",
    "-c:v", "copy",
    "fragman.mp4"
], check=True)

# Callback
requests.post(
    callback,
    files={"video": open("fragman.mp4", "rb")},
    data={"film_id": film_id}
)

print("✅ Fragman gönderildi")
