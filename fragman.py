#!/usr/bin/env python3
"""
fragman.py - YouTube'dan fragman indir, TTS sesi ile birleştir
PHP callback sisteminize uygun şekilde
"""

import os
import json
import requests
import subprocess
import yt_dlp
import tempfile
import shutil

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
    exit(1)

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
    tts_duration = 180  # fallback süre

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
        
        # Önce resmi trailer'ı bul
        for video in data.get('results', []):
            if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                video_id = video['key']
                title = video.get('name', 'Trailer')
                print(f"🎯 Resmi trailer bulundu: {title}")
                return f"https://www.youtube.com/watch?v={video_id}"
        
        # Trailer yoksa herhangi bir YouTube videosu
        for video in data.get('results', []):
            if video.get('site') == 'YouTube':
                video_id = video['key']
                title = video.get('name', 'Video')
                print(f"📹 YouTube videosu bulundu: {title}")
                return f"https://www.youtube.com/watch?v={video_id}"
                
    except Exception as e:
        print(f"❌ TMDB hatası: {e}")
    
    return None

print("🔍 TMDB'den YouTube fragmanı aranıyor...")
youtube_url = get_youtube_trailer(tmdb_id, TMDB_KEY)

if not youtube_url:
    print("❌ YouTube fragmanı bulunamadı")
    exit(1)

print(f"📹 YouTube URL: {youtube_url}")

# ============================================
# 5️⃣ YOUTUBE'DAN FRAGMAN İNDİR
# ============================================
# ============================================
# 5️⃣ YOUTUBE'DAN FRAGMAN İNDİR
# ============================================
print("📥 YouTube'dan fragman indiriliyor...")
trailer_file = f"trailer_{film_id}.mp4"

# YENİ: Güncellenmiş ydl_opts - Anti-bot önlemlerini aşmak için
ydl_opts = {
    'format': 'best[height<=720]',
    'outtmpl': trailer_file,
    'quiet': False,
    'no_warnings': False,
    'extract_flat': False,
    'noplaylist': True,
    'socket_timeout': 30,
    'retries': 10,
    'fragment_retries': 10,
    'skip_unavailable_fragments': True,
    # YENİ EKLENEN: Anti-bot parametreleri
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],  # Mobil/Web client kullan
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
    },
    # YENİ: Cookie dosyası kullan (eğer varsa)
    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
}

print("🔄 YouTube'a özel parametrelerle indirme deneniyor...")

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Önce video bilgilerini al (indirme yapmadan)
        print("📊 Video bilgileri alınıyor...")
        info = ydl.extract_info(youtube_url, download=False)
        print(f"✅ Video bilgileri: {info['title']}")
        print(f"   📏 Çözünürlük: {info.get('height', 'N/A')}p")
        print(f"   ⏱️  Süre: {info.get('duration', 'N/A')} saniye")
        
        # Şimdi indir
        print("⬇️  Video indiriliyor...")
        ydl.download([youtube_url])
        print(f"✅ Fragman indirildi: {info['title']}")
        
except Exception as e:
    print(f"❌ YouTube indirme hatası: {e}")
    
    # ALTERNATİF: Daha basit format deneyelim
    print("🔄 Alternatif yöntem deneniyor...")
    try:
        alt_opts = {
            'format': '18',  # 360p MP4 - daha az sorun çıkaran format
            'outtmpl': trailer_file,
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(alt_opts) as ydl:
            ydl.download([youtube_url])
        print("✅ Alternatif yöntemle indirildi")
    except Exception as e2:
        print(f"❌ Alternatif yöntem de başarısız: {e2}")
        exit(1)

# ============================================
# 6️⃣ FRAGMAN SÜRESİNİ ÖLÇ
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
# 7️⃣ VİDEO VE SESİ BİRLEŞTİR
# ============================================
# Hangi süreyi kullanacağımızı belirle
# TTS veya fragmandan hangisi daha kısa?
target_duration = min(tts_duration, trailer_duration)
print(f"🎯 Hedef süre: {target_duration:.2f} saniye")

output_file = f"fragman_{film_id}.mp4"

# FFmpeg komutu: Fragmanı kısalt, ses seviyesini düşür, TTS ekle
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-i", trailer_file,
    "-i", mp3_file,
    "-filter_complex",
    # Video: ilk target_duration saniyesini al, 720p'ye scale et
    f"[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
    f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
    f"trim=duration={target_duration},setpts=PTS-STARTPTS[video];"
    
    # Orijinal ses: ilk target_duration saniyesini al, ses seviyesini %20'ye düşür
    f"[0:a]atrim=duration={target_duration},asetpts=PTS-STARTPTS,"
    f"volume=0.2[orig_audio];"
    
    # TTS sesi: ilk target_duration saniyesini al
    f"[1:a]atrim=duration={target_duration},asetpts=PTS-STARTPTS[tts_audio];"
    
    # Sesleri birleştir
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
    subprocess.run(ffmpeg_cmd, check=True, capture_output=False)
    print(f"✅ Video işlendi: {output_file}")
except subprocess.CalledProcessError as e:
    print(f"❌ FFmpeg hatası: {e}")
    exit(1)

# ============================================
# 8️⃣ DOSYA BOYUTUNU KONTROL ET
# ============================================
file_size = os.path.getsize(output_file)
print(f"💾 Dosya boyutu: {file_size / (1024*1024):.2f} MB")

if file_size == 0:
    print("❌ Oluşturulan video boş!")
    exit(1)

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
        print(f"📨 Yanıt: {response.text}")
        
        if response.status_code == 200:
            print("✅ Callback başarılı!")
        else:
            print(f"❌ Callback hatası: {response.status_code}")
            
except Exception as e:
    print(f"❌ Callback gönderme hatası: {e}")
    exit(1)

# ============================================
# 🔟 TEMİZLİK
# ============================================
print("🧹 Geçici dosyalar temizleniyor...")
for temp_file in [mp3_file, trailer_file, output_file]:
    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
            print(f"   - Silindi: {temp_file}")
        except Exception as e:
            print(f"   - Silinemedi {temp_file}: {e}")

print("🎉 Fragman işlemi tamamlandı!")
