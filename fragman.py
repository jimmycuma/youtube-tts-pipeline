import os, json, requests, subprocess

event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
p = event["client_payload"]

film_id  = p["film_id"]        # ✅ DÜZELTİLDİ
tmdb_id  = p["tmdb_id"]
film_adi = p["film_adi"]
ses_url  = p["ses_url"]
callback = p["callback"]

TMDB_KEY = os.environ["TMDB_API_KEY"]

print("🎬 Film:", film_adi)

# 1️⃣ MP3 indir
mp3 = f"ses_{film_id}.mp3"
open(mp3, "wb").write(requests.get(ses_url).content)

# 2️⃣ Süre (ffprobe yoksa ffmpeg)
try:
    duration = subprocess.check_output([
        "ffprobe", "-i", mp3,
        "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ]).decode().strip()
    duration = int(float(duration))
except:
    duration = 180  # fallback

duration += 10
print("⏱ Süre:", duration)

# 3️⃣ TMDB verisi
tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_KEY}"
data = requests.get(tmdb_url).json()

if not data.get("backdrop_path"):
    raise Exception("⛔ Backdrop yok")

poster_url   = "https://image.tmdb.org/t/p/w500" + data["poster_path"] if data.get("poster_path") else None
backdrop_url = "https://image.tmdb.org/t/p/original" + data["backdrop_path"]

if poster_url:
    open("poster.jpg", "wb").write(requests.get(poster_url).content)

open("backdrop.jpg", "wb").write(requests.get(backdrop_url).content)

# 4️⃣ Kapak
subprocess.run([
    "ffmpeg", "-y",
    "-loop", "1", "-i", "backdrop.jpg",
    "-loop", "1", "-i", "poster.jpg" if poster_url else "backdrop.jpg",
    "-loop", "1", "-i", "assets/logo.png",
    "-filter_complex",
    "[0:v]scale=1920:1080,boxblur=20[bg];"
    "[1:v]scale=480:-1[poster];"
    "[bg][poster]overlay=(W-w)/2:(H-h)/2[tmp];"
    "[tmp][2:v]overlay=W-w-40:H-h-40",
    "-t", "4",
    "cover.mp4"
], check=True)

# 5️⃣ Film adı
subprocess.run([
    "ffmpeg", "-y",
    "-i", "cover.mp4",
    "-vf",
    f"drawtext=fontfile=/home/runner/work/youtube-tts-pipeline/youtube-tts-pipeline/assets/font.ttf:"
    f"text='{film_adi}':fontsize=64:fontcolor=white:"
    f"x=(w-text_w)/2:y=h*0.75",
    "cover_text.mp4"
], check=True)

# 6️⃣ Görsel akış
subprocess.run([
    "ffmpeg", "-y",
    "-loop", "1", "-i", "backdrop.jpg",
    "-vf",
    "scale=1920:1080,zoompan=z='min(zoom+0.0004,1.1)':d=300",
    "-t", str(duration),
    "visuals.mp4"
], check=True)

# 7️⃣ Birleştir
subprocess.run([
    "ffmpeg", "-y",
    "-i", "cover_text.mp4",
    "-i", "visuals.mp4",
    "-i", mp3,
    "-filter_complex",
    "[0:v][1:v]concat=n=2:v=1:a=0[v]",
    "-map", "[v]",
    "-map", "2:a",
    "-shortest",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "fragman.mp4"
], check=True)

# 8️⃣ Callback
requests.post(
    callback,
    files={"video": open("fragman.mp4", "rb")},
    data={"film_id": film_id},   # ✅ DÜZELTİLDİ
    timeout=120
)

print("✅ Fragman hazır ve gönderildi")
