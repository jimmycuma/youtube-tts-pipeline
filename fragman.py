import os, json, requests, subprocess

event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
p = event["client_payload"]

film_id   = p["film_id"]
tmdb_id   = p["tmdb_id"]
film_adi  = p["film_adi"]
ses_url   = p["ses_url"]
callback  = p["callback"]

TMDB_KEY = os.environ["TMDB_API_KEY"]

print("🎬 Film:", film_adi)

# 1️⃣ MP3 indir
mp3 = f"ses_{film_id}.mp3"
open(mp3, "wb").write(requests.get(ses_url).content)

# 2️⃣ MP3 süresi
duration = subprocess.check_output([
    "ffprobe", "-i", mp3,
    "-show_entries", "format=duration",
    "-v", "quiet", "-of", "csv=p=0"
]).decode().strip()

duration = int(float(duration)) + 10
print("⏱ Süre:", duration)

# 3️⃣ TMDB trailer bul
url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos?api_key={TMDB_KEY}&language=tr-TR"
videos = requests.get(url).json()["results"]

trailer = None
for v in videos:
    if v["type"] == "Trailer" and v["site"] == "Apple Trailers":
        trailer = v
        break

if not trailer:
    trailer = next((v for v in videos if v["type"] == "Trailer"), None)

if not trailer:
    raise Exception("⛔ Trailer bulunamadı")

video_url = trailer["key"]  # Apple CDN linki

# 4️⃣ Trailer indir
subprocess.run([
    "ffmpeg", "-y",
    "-i", video_url,
    "-t", str(duration),
    "-c", "copy",
    "video.mp4"
], check=True)

# 5️⃣ Sesle birleştir
subprocess.run([
    "ffmpeg", "-y",
    "-i", "video.mp4",
    "-i", mp3,
    "-shortest",
    "-c:v", "copy",
    "fragman.mp4"
], check=True)

# 6️⃣ Callback
requests.post(
    callback,
    files={"video": open("fragman.mp4", "rb")},
    data={"film_id": film_id},
    timeout=120
)

print("✅ Fragman gönderildi")
