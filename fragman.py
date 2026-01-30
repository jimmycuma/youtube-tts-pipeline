#!/usr/bin/env python3
"""
fragman.py - Cookie'siz YouTube indirme sistemi
3 Katmanlı: Invidious → Piped → Smart yt-dlp → TMDB Fallback
"""

import os
import json
import requests
import subprocess
import time
import random
import sys

# ============================================
# KATMAN 1: INVIDIOUS API (AÇIK KAYNAK)
# ============================================
def download_via_invidious(video_id, output_file):
    """Invidious API ile YouTube videosu indir"""
    
    # Public Invidious Instances (otomatik güncellenir)
    INV_INSTANCES = [
        'https://inv.riverside.rocks',
        'https://invidious.nerdvpn.de', 
        'https://yt.artemislena.eu',
        'https://invidious.flokinet.to',
        'https://inv.us.projectsegfau.lt',
        'https://invidious.weblibre.org'
    ]
    
    for instance in INV_INSTANCES:
        try:
            print(f"🔄 Invidious: {instance}")
            
            # Video bilgilerini al
            api_url = f"{instance}/api/v1/videos/{video_id}"
            response = requests.get(api_url, timeout=15)
            video_info = response.json()
            
            # Formatları ara (720p veya 480p)
            formats = video_info.get('formatStreams', []) + video_info.get('adaptiveFormats', [])
            
            for fmt in formats:
                quality = fmt.get('quality', '')
                mime_type = fmt.get('type', '')
                video_url = fmt.get('url', '')
                
                if ('720p' in str(quality) or '480p' in str(quality)) and 'video/mp4' in mime_type:
                    print(f"✅ Format bulundu: {quality}")
                    
                    # FFmpeg ile indir
                    cmd = [
                        'ffmpeg', '-y',
                        '-headers', f'Referer: {instance}\r\nUser-Agent: Mozilla/5.0',
                        '-i', video_url,
                        '-c', 'copy',
                        '-timeout', '30000000',  # 30 saniye timeout
                        output_file
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    
                    if result.returncode == 0 and os.path.exists(output_file):
                        file_size = os.path.getsize(output_file)
                        if file_size > 102400:  # 100KB'den büyükse
                            print(f"✅ Invidious ile indirildi ({file_size/1024/1024:.1f} MB)")
                            return True
                    
        except Exception as e:
            print(f"⚠️ Invidious {instance} hatası: {str(e)[:100]}")
            continue
    
    return False

# ============================================
# KATMAN 2: PIPED API 
# ============================================
def download_via_piped(video_id, output_file):
    """Piped API ile indir"""
    
    PIPED_INSTANCES = [
        'https://pipedapi.kavin.rocks',
        'https://pipedapi.moomoo.me',
        'https://pipedapi-libre.kavin.rocks',
        'https://pipedapi.syncpundit.io'
    ]
    
    for instance in PIPED_INSTANCES:
        try:
            print(f"🔄 Piped: {instance}")
            
            api_url = f"{instance}/streams/{video_id}"
            response = requests.get(api_url, timeout=15)
            data = response.json()
            
            # Video stream'lerini ara
            for video in data.get('videoStreams', []):
                if video.get('quality') in ['720p', '480p', '360p']:
                    video_url = video['url']
                    
                    # wget ile indir
                    cmd = [
                        'wget', '--quiet',
                        '--timeout=60',
                        '--tries=3',
                        '-O', output_file,
                        video_url
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, timeout=120)
                    
                    if result.returncode == 0 and os.path.exists(output_file):
                        file_size = os.path.getsize(output_file)
                        if file_size > 102400:
                            print(f"✅ Piped ile indirildi ({file_size/1024/1024:.1f} MB)")
                            return True
                    
        except Exception as e:
            print(f"⚠️ Piped {instance} hatası: {str(e)[:100]}")
            continue
    
    return False

# ============================================
# KATMAN 3: SMART YT-DLP (SON ÇARE)
# ============================================
def download_smart_ytdlp(youtube_url, output_file):
    """Akıllı yt-dlp ile indir"""
    
    try:
        import yt_dlp
    except ImportError:
        print("⚠️ yt-dlp kurulu değil, atlanıyor...")
        return False
    
    # Bot user-agent'ları
    BOT_AGENTS = [
        'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)',
        'Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)',
        'Mozilla/5.0 (compatible; DuckDuckBot/1.0; +http://duckduckgo.com/duckduckbot.html)'
    ]
    
    for attempt in range(2):  # 2 deneme
        try:
            print(f"🔄 yt-dlp deneme {attempt+1}/2")
            
            ydl_opts = {
                'format': random.choice(['18', '22', '136+140']),  # 360p, 720p, etc
                'outtmpl': output_file,
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                'sleep_interval': random.randint(2, 5),
                'max_sleep_interval': random.randint(10, 20),
                'http_headers': {
                    'User-Agent': random.choice(BOT_AGENTS),
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Referer': random.choice(['https://www.google.com', 'https://www.reddit.com']),
                    'DNT': '1',
                },
                'cookiefile': None,  # NO COOKIES
                'nocheckcertificate': True,
                'geo_bypass': True,
                'geo_bypass_country': random.choice(['US', 'DE', 'TR', 'FR', 'JP']),
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                time.sleep(random.uniform(1, 3))
                ydl.download([youtube_url])
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 102400:
                print(f"✅ yt-dlp ile indirildi")
                return True
                
        except Exception as e:
            print(f"⚠️ yt-dlp hatası: {str(e)[:100]}")
            time.sleep(random.randint(5, 10))
    
    return False

# ============================================
# FALLBACK: TMDB GÖRSELLERİNDEN VİDEO
# ============================================
def create_video_from_tmdb(tmdb_id, film_adi, duration, output_file):
    """TMDB'den görsel indir, video oluştur"""
    
    try:
        print(f"🎨 TMDB'den görsel videosu oluşturuluyor...")
        
        # TMDB API Key
        TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
        if not TMDB_KEY:
            print("❌ TMDB_API_KEY bulunamadı")
            return False
        
        # Film detaylarını al
        tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
        params = {'api_key': TMDB_KEY, 'language': 'tr-TR'}
        response = requests.get(tmdb_url, params=params, timeout=15)
        film_data = response.json()
        
        # Görsel URL'sini belirle (backdrop > poster)
        image_url = None
        if film_data.get('backdrop_path'):
            image_url = f"https://image.tmdb.org/t/p/original{film_data['backdrop_path']}"
        elif film_data.get('poster_path'):
            image_url = f"https://image.tmdb.org/t/p/w500{film_data['poster_path']}"
        
        if not image_url:
            print("❌ Görsel bulunamadı")
            return False
        
        # Görseli indir
        img_file = f"temp_image_{tmdb_id}.jpg"
        print(f"📥 Görsel indiriliyor: {image_url}")
        
        img_response = requests.get(image_url, timeout=30)
        with open(img_file, 'wb') as f:
            f.write(img_response.content)
        
        # Görselden video oluştur (zoom efekti)
        print("🔨 Görselden video render ediliyor...")
        
        # Basit siyah background fallback
        if not os.path.exists(img_file) or os.path.getsize(img_file) < 1024:
            print("⚠️ Görsel indirilemedi, siyah video oluşturuluyor...")
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'color=c=black:s=1280x720:d={duration}:r=25',
                '-vf', f"drawtext=text='{film_adi}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                output_file
            ]
        else:
            # Görselden zoom efekti ile video
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1',
                '-i', img_file,
                '-vf', f"scale=1280:720:force_original_aspect_ratio=decrease,"
                       f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                       f"zoompan=z='min(zoom+0.001,1.3)':d={int(duration*25)}:s=1280x720,"
                       f"drawtext=text='{film_adi}':fontcolor=white:fontsize=36:box=1:boxcolor=black@0.5:x=(w-text_w)/2:y=h-100",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                '-t', str(duration),
                output_file
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Temizlik
        if os.path.exists(img_file):
            os.remove(img_file)
        
        if result.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ Görsel videosu oluşturuldu ({file_size/1024/1024:.1f} MB)")
            return True
        else:
            print(f"❌ FFmpeg hatası: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ TMDB video oluşturma hatası: {e}")
        return False

# ============================================
# YARDIMCI FONKSİYONLAR
# ============================================
def extract_video_id(url):
    """YouTube URL'den video ID çıkar"""
    if 'v=' in url:
        return url.split('v=')[1].split('&')[0]
    elif 'youtu.be/' in url:
        return url.split('youtu.be/')[1].split('?')[0]
    else:
        return url.split('/')[-1]

def get_youtube_from_tmdb(tmdb_id, api_key):
    """TMDB'den YouTube URL'sini al"""
    try:
        tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
        params = {'api_key': api_key, 'language': 'tr-TR'}
        response = requests.get(tmdb_url, params=params, timeout=15)
        data = response.json()
        
        for video in data.get('results', []):
            if video.get('site') == 'YouTube' and video.get('type') in ['Trailer', 'Teaser']:
                video_id = video['key']
                return f"https://www.youtube.com/watch?v={video_id}"
        
        # Herhangi bir YouTube videosu
        for video in data.get('results', []):
            if video.get('site') == 'YouTube':
                video_id = video['key']
                return f"https://www.youtube.com/watch?v={video_id}"
                
    except Exception as e:
        print(f"❌ TMDB YouTube sorgu hatası: {e}")
    
    return None

def mix_audio_video(video_path, audio_path, output_path):
    """Video ve sesi birleştir"""
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(output_path):
            return True
        else:
            print(f"⚠️ Mix hatası: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Mix işlemi hatası: {e}")
        return False

# ============================================
# ANA İŞLEM FONKSİYONU
# ============================================
def download_youtube_3layer(youtube_url, output_file, tmdb_id, film_adi, fallback_duration=180):
    """3 katmanlı indirme sistemi"""
    
    # Video ID'yi çıkar
    video_id = extract_video_id(youtube_url)
    print(f"🎯 Video ID: {video_id}")
    
    # KATMAN 1: Invidious API
    print("\n" + "="*50)
    print("1. KATMAN: Invidious API")
    print("="*50)
    if download_via_invidious(video_id, output_file):
        return True
    
    # KATMAN 2: Piped API
    print("\n" + "="*50)
    print("2. KATMAN: Piped API") 
    print("="*50)
    if download_via_piped(video_id, output_file):
        return True
    
    # KATMAN 3: Smart yt-dlp
    print("\n" + "="*50)
    print("3. KATMAN: Smart yt-dlp")
    print("="*50)
    if download_smart_ytdlp(youtube_url, output_file):
        return True
    
    # FALLBACK: TMDB Görsel Videosu
    print("\n" + "="*50)
    print("FALLBACK: TMDB Görsel Videosu")
    print("="*50)
    if create_video_from_tmdb(tmdb_id, film_adi, fallback_duration, output_file):
        return True
    
    return False

# ============================================
# ANA PROGRAM
# ============================================
def main():
    # GitHub event verilerini al
    event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
    p = event["client_payload"]
    
    film_id = p["film_id"]
    tmdb_id = p["tmdb_id"]
    film_adi = p["film_adi"]
    ses_url = p["ses_url"]
    callback = p["callback"]
    
    TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
    if not TMDB_KEY:
        print("❌ TMDB_API_KEY ortam değişkeni bulunamadı!")
        sys.exit(1)
    
    print(f"🎬 Film: {film_adi}")
    print(f"🆔 Film ID: {film_id}, TMDB ID: {tmdb_id}")
    print("🚫 Cookie'siz 3-Katmanlı Sistem Aktif\n")
    
    # 1. YouTube URL'sini TMDB'den al
    print("🔍 TMDB'den YouTube URL'si aranıyor...")
    youtube_url = get_youtube_from_tmdb(tmdb_id, TMDB_KEY)
    
    if not youtube_url:
        print("❌ YouTube URL bulunamadı, direkt Fallback'e geçiliyor...")
        youtube_url = None
    
    # 2. TTS sesini indir
    print("\n🔊 TTS sesi indiriliyor...")
    mp3_file = f"ses_{film_id}.mp3"
    try:
        response = requests.get(ses_url, timeout=30)
        with open(mp3_file, 'wb') as f:
            f.write(response.content)
        
        # TTS süresini ölç
        try:
            duration_cmd = [
                "ffprobe", "-i", mp3_file,
                "-show_entries", "format=duration",
                "-v", "quiet", "-of", "csv=p=0"
            ]
            duration = subprocess.check_output(duration_cmd, stderr=subprocess.DEVNULL).decode().strip()
            tts_duration = float(duration)
            print(f"⏱️ TTS süresi: {tts_duration:.1f} saniye")
        except:
            tts_duration = 180
            print(f"⚠️ TTS süresi ölçülemedi, varsayılan: {tts_duration}s")
            
    except Exception as e:
        print(f"❌ TTS indirme hatası: {e}")
        tts_duration = 180
    
    # 3. YouTube veya Fallback ile video al
    trailer_file = f"trailer_{film_id}.mp4"
    video_obtained = False
    
    if youtube_url:
        print(f"\n📹 YouTube URL: {youtube_url}")
        video_obtained = download_youtube_3layer(
            youtube_url, 
            trailer_file, 
            tmdb_id, 
            film_adi,
            tts_duration
        )
    else:
        print("\n⚠️ YouTube URL yok, direkt Fallback...")
        video_obtained = create_video_from_tmdb(tmdb_id, film_adi, tts_duration, trailer_file)
    
    if not video_obtained:
        print("❌ TÜM YÖNTEMLER BAŞARISIZ!")
        sys.exit(1)
    
    # 4. Video ve sesi birleştir
    print("\n🔗 Video ve ses birleştiriliyor...")
    final_file = f"fragman_{film_id}.mp4"
    
    if mix_audio_video(trailer_file, mp3_file, final_file):
        print(f"✅ Birleştirme tamam: {final_file}")
    else:
        print("❌ Birleştirme başarısız, sadece video gönderiliyor...")
        final_file = trailer_file
    
    # 5. Callback'e gönder
    print(f"\n📤 Callback'e gönderiliyor: {callback}")
    try:
        with open(final_file, 'rb') as video_file:
            files = {'video': (f'fragman_{film_id}.mp4', video_file, 'video/mp4')}
            data = {'film_id': film_id}
            
            response = requests.post(
                callback,
                files=files,
                data=data,
                timeout=180
            )
            
            print(f"📡 HTTP {response.status_code}")
            print(f"📨 Yanıt: {response.text[:100]}")
            
    except Exception as e:
        print(f"❌ Callback hatası: {e}")
    
    # 6. Temizlik
    print("\n🧹 Temizlik yapılıyor...")
    for temp_file in [mp3_file, trailer_file]:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
    
    if final_file != trailer_file and os.path.exists(final_file):
        try:
            os.remove(final_file)
        except:
            pass
    
    print("\n🎉 TAMAMLANDI!")

if __name__ == "__main__":
    main()
