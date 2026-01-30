#!/usr/bin/env python3
"""
fragman.py - YouTube'dan fragman indir, TTS sesi ile birleştir
Hibrit çözüm: hem yt-dlp hem pytube kullanır
"""

import os
import json
import requests
import subprocess
import sys

# ============================================
# 1️⃣ GITHUB EVENT VERİLERİNİ AL
# ============================================
event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
p = event["client_payload"]

film_id  = p["film_id"]
tmdb_id  = p["tmdb_id"]
film_adi = p["film_adi"]
ses_url  = p["ses_url"]
callback = p["callback"]

TMDB_KEY = os.environ["TMDB_API_KEY"]

print(f"🎬 Film: {film_adi}")
print(f"🆔 Film ID: {film_id}, TMDB ID: {tmdb_id}")

# ============================================
# 2️⃣ TTS SESİNİ İNDİR
# ============================================
print("🔊 TTS sesi indiriliyor...")
mp3_file = f"ses_{film_id}.mp3"
try:
    response = requests.get(ses_url, timeout=30)
    response.raise_for_status()
    with open(mp3_file, "wb") as f:
        f.write(response.content)
    print(f"✅ TTS indirildi: {mp3_file} ({os.path.getsize(mp3_file)} bytes)")
except Exception as e:
    print(f"❌ TTS indirme hatası: {e}")
    sys.exit(1)

# ============================================
# 3️⃣ TTS SÜRESİNİ ÖLÇ
# ============================================
try:
    duration_cmd = [
        "ffprobe", "-i", mp3_file,
        "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ]
    duration = subprocess.check_output(duration_cmd).decode().strip()
    tts_duration = float(duration)
    print(f"⏱️ TTS süresi: {tts_duration:.2f} saniye")
except Exception as e:
    print(f"⚠️ FFprobe çalışmadı, varsayılan süre kullanılıyor: {e}")
    tts_duration = 180

# ============================================
# 4️⃣ TMDB'DEN YOUTUBE FRAGMAN URL'SİNİ BUL
# ============================================
def get_youtube_trailer(tmdb_id, api_key):
    """TMDB'den YouTube trailer URL'sini al"""
    tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
    params = {
        'api_key': api_key,
        'language': 'tr-TR'
    }
    
    try:
        response = requests.get(tmdb_url, params=params, timeout=10)
        data = response.json()
        
        for video in data.get('results', []):
            if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                video_id = video['key']
                print(f"🎯 Resmi trailer bulundu: {video.get('name', 'Trailer')}")
                return f"https://www.youtube.com/watch?v={video_id}"
        
        for video in data.get('results', []):
            if video.get('site') == 'YouTube':
                video_id = video['key']
                print(f"📹 YouTube videosu bulundu: {video.get('name', 'Video')}")
                return f"https://www.youtube.com/watch?v={video_id}"
                
    except Exception as e:
        print(f"❌ TMDB hatası: {e}")
    
    return None

print("🔍 TMDB'den YouTube fragmanı aranıyor...")
youtube_url = get_youtube_trailer(tmdb_id, TMDB_KEY)

if not youtube_url:
    print("❌ YouTube fragmanı bulunamadı")
    sys.exit(1)

print(f"📹 YouTube URL: {youtube_url}")

# ============================================
# 5️⃣ HİBRİT YOUTUBE İNDİRME FONKSİYONU
# ============================================
def download_youtube_video_hybrid(url, output_file):
    """İki yöntemle YouTube videosunu indir"""
    
    # YÖNTEM 1: yt-dlp ile dene
    print("🔄 1. yöntem: yt-dlp ile indirme deneniyor...")
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'best[height<=720]',
            'outtmpl': output_file,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36',
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
            print("✅ yt-dlp ile indirildi")
            return True
    except Exception as e:
        print(f"❌ yt-dlp hatası: {e}")
    
    # YÖNTEM 2: pytube ile dene
    print("🔄 2. yöntem: pytube ile indirme deneniyor...")
    try:
        from pytube import YouTube
        
        yt = YouTube(url)
        
        # En iyi progressive stream'i bul
        stream = yt.streams.filter(
            progressive=True,
            file_extension='mp4'
        ).order_by('resolution').desc().first()
        
        if stream:
            print(f"📥 pytube stream: {stream.resolution}")
            stream.download(filename=output_file)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
                print("✅ pytube ile indirildi")
                return True
    except Exception as e:
        print(f"❌ pytube hatası: {e}")
    
    # YÖNTEM 3: Basit format ID ile dene
    print("🔄 3. yöntem: Basit format ile deneniyor...")
    try:
        simple_opts = {
            'format': '18',  # 360p - en güvenilir format
            'outtmpl': output_file,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(simple_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(output_file):
            print("✅ Basit format ile indirildi")
            return True
    except Exception as e:
        print(f"❌ Basit format hatası: {e}")
    
    return False

# ============================================
# 6️⃣ FRAGMAN İNDİR
# ============================================
print("📥 YouTube'dan fragman indiriliyor...")
trailer_file = f"trailer_{film_id}.mp4"

if not download_youtube_video_hybrid(youtube_url, trailer_file):
    print("❌ Tüm indirme yöntemleri başarısız")
    sys.exit(1)

# ============================================
# 7️⃣ FRAGMAN SÜRESİNİ ÖLÇ
# ============================================
try:
    duration_cmd = [
        "ffprobe", "-i", trailer_file,
        "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ]
    duration = subprocess.check_output(duration_cmd).decode().strip()
    trailer_duration = float(duration)
    print(f"⏱️ Fragman süresi: {trailer_duration:.2f} saniye")
except Exception as e:
    print(f"⚠️ Fragman süresi ölçülemedi: {e}")
    trailer_duration = tts_duration

# ============================================
# 8️⃣ VİDEO VE SESİ BİRLEŞTİR
# ============================================
target_duration = min(tts_duration, trailer_duration)
print(f"🎯 Hedef süre: {target_duration:.2f} saniye")

output_file = f"fragman_{film_id}.mp4"

# FFmpeg komutu
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-i", trailer_file,
    "-i", mp3_file,
    "-filter_complex",
    f"[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
    f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
    f"trim=duration={target_duration},setpts=PTS-STARTPTS[video];"
    f"[0:a]atrim=duration={target_duration},asetpts=PTS-STARTPTS,"
    f"volume=0.2[orig_audio];"
    f"[1:a]atrim=duration={target_duration},asetpts=PTS-STARTPTS[tts_audio];"
    f"[orig_audio][tts_audio]amix=inputs=2:duration=longest[final_audio]",
    "-map", "[video]",
    "-map", "[final_audio]",
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "23",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    output_file
]

print("🔨 Video ve ses birleştiriliyor...")
try:
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"✅ Video işlendi: {output_file}")
except subprocess.CalledProcessError as e:
    print(f"❌ FFmpeg hatası: {e}")
    sys.exit(1)

# ============================================
# 9️⃣ CALLBACK'E GÖNDER
# ============================================
print(f"📤 Callback'e gönderiliyor: {callback}")
try:
    with open(output_file, 'rb') as video_file:
        files = {'video': (f'fragman_{film_id}.mp4', video_file, 'video/mp4')}
        data = {'film_id': film_id}
        
        response = requests.post(
            callback,
            files=files,
            data=data,
            timeout=120
        )
        
        print(f"📡 HTTP {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Callback başarılı!")
        else:
            print(f"❌ Callback hatası: {response.text}")
            
except Exception as e:
    print(f"❌ Callback gönderme hatası: {e}")

# ============================================
# 🔟 TEMİZLİK
# ============================================
print("🧹 Temizlik...")
for temp_file in [mp3_file, trailer_file, output_file]:
    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except:
            pass

print("🎉 Tamamlandı!")
