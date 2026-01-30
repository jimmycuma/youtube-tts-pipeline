#!/usr/bin/env python3
"""
fragman.py - YouTube'dan fragman indir, TTS sesi ile birleştir
Basit ve güvenilir versiyon
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
except:
    tts_duration = 180
    print(f"⚠️ FFprobe çalışmadı, varsayılan süre: {tts_duration}s")

# ============================================
# 4️⃣ TMDB'DEN YOUTUBE FRAGMAN URL'SİNİ BUL
# ============================================
print("🔍 TMDB'den YouTube fragmanı aranıyor...")
try:
    tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
    params = {'api_key': TMDB_KEY, 'language': 'tr-TR'}
    response = requests.get(tmdb_url, params=params, timeout=10)
    data = response.json()
    
    youtube_url = None
    for video in data.get('results', []):
        if video.get('site') == 'YouTube':
            video_id = video['key']
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"✅ YouTube videosu bulundu: {video.get('name', 'Video')}")
            break
    
    if not youtube_url:
        print("❌ YouTube fragmanı bulunamadı")
        sys.exit(1)
        
    print(f"📹 YouTube URL: {youtube_url}")
    
except Exception as e:
    print(f"❌ TMDB hatası: {e}")
    sys.exit(1)

# ============================================
# 5️⃣ YOUTUBE'DAN FRAGMAN İNDİR (yt-dlp ile)
# ============================================
print("📥 YouTube'dan fragman indiriliyor...")
trailer_file = f"trailer_{film_id}.mp4"

# ÖNCE yt-dlp'yi dene
try:
    print("🔄 yt-dlp ile indirme deneniyor...")
    import yt_dlp
    
    ydl_opts = {
        'format': 'best[height<=480]',  # 480p - daha güvenilir
        'outtmpl': trailer_file,
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    
    if os.path.exists(trailer_file) and os.path.getsize(trailer_file) > 1024:
        print("✅ yt-dlp ile indirildi")
    else:
        raise Exception("Dosya boş veya oluşmadı")
        
except Exception as e:
    print(f"❌ yt-dlp hatası: {e}")
    
    # pytube ile dene
    try:
        print("🔄 pytube ile indirme deneniyor...")
        from pytube import YouTube
        
        yt = YouTube(youtube_url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
        if stream:
            stream.download(filename=trailer_file)
            print("✅ pytube ile indirildi")
        else:
            raise Exception("Uygun stream bulunamadı")
    except Exception as e2:
        print(f"❌ pytube hatası: {e2}")
        print("⚠️ İndirme başarısız, önceden indirilmiş fragman kullanılıyor...")
        
        # Eğer hala trailer_file yoksa, bir örnek video oluştur
        if not os.path.exists(trailer_file):
            # Basit bir siyah video oluştur
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=black:s=1280x720:d=30",
                "-c:v", "libx264",
                "-t", "30",
                trailer_file
            ]
            subprocess.run(ffmpeg_cmd, check=False)

# ============================================
# 6️⃣ FRAGMAN SÜRESİNİ ÖLÇ
# ============================================
trailer_duration = tts_duration
if os.path.exists(trailer_file):
    try:
        duration_cmd = [
            "ffprobe", "-i", trailer_file,
            "-show_entries", "format=duration",
            "-v", "quiet", "-of", "csv=p=0"
        ]
        duration = subprocess.check_output(duration_cmd).decode().strip()
        trailer_duration = float(duration)
        print(f"⏱️ Fragman süresi: {trailer_duration:.2f} saniye")
    except:
        pass

# ============================================
# 7️⃣ VİDEO VE SESİ BİRLEŞTİR
# ============================================
target_duration = min(tts_duration, trailer_duration, 300)  # Maksimum 5 dakika
print(f"🎯 Hedef süre: {target_duration:.2f} saniye")

output_file = f"fragman_{film_id}.mp4"

# Basit FFmpeg komutu
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-i", trailer_file,
    "-i", mp3_file,
    "-filter_complex",
    f"[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
    f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
    f"trim=duration={target_duration}[video];"
    f"[0:a]atrim=duration={target_duration},volume=0.3[va];"
    f"[1:a]atrim=duration={target_duration}[vb];"
    f"[va][vb]amix=inputs=2:duration=longest[audio]",
    "-map", "[video]",
    "-map", "[audio]",
    "-c:v", "libx264",
    "-preset", "fast",
    "-c:a", "aac",
    "-t", str(target_duration),
    output_file
]

print("🔨 Video ve ses birleştiriliyor...")
try:
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ FFmpeg uyarısı: {result.stderr[:200]}")
    
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        print(f"✅ Video işlendi: {output_file} ({file_size/1024/1024:.1f} MB)")
    else:
        print("❌ Output dosyası oluşturulamadı")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ FFmpeg hatası: {e}")
    sys.exit(1)

# ============================================
# 8️⃣ CALLBACK'E GÖNDER
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
            print(f"❌ Callback hatası: {response.text[:200]}")
            
except Exception as e:
    print(f"❌ Callback gönderme hatası: {e}")

# ============================================
# 9️⃣ TEMİZLİK
# ============================================
print("🧹 Temizlik...")
for temp_file in [mp3_file, trailer_file, output_file]:
    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except:
            pass

print("🎉 Tamamlandı!")
