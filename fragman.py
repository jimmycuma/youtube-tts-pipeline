#!/usr/bin/env python3
"""
fragman.py - Gelişmiş yt-dlp + TMDB Fallback (Cookie'siz)
Katman: 1. Akıllı yt-dlp → 2. TMDB Fallback
"""

import os, json, requests, subprocess, time, random, sys

# ============================================
# 1. KATMAN: GELİŞMİŞ YT-DLP (Cookie'siz)
# ============================================
def download_ytdlp_enhanced(youtube_url, output_file, max_attempts=5):
    """Gelişmiş yt-dlp ile YouTube videosu indir"""
    
    for attempt in range(max_attempts):
        try:
            # Rastgele kimlik oluştur (Her denemede farklı)
            user_agent = random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
            ])
            
            referer = random.choice([
                'https://www.google.com/',
                'https://www.youtube.com/',
                'https://www.reddit.com/',
                'https://www.facebook.com/',
                'https://www.twitter.com/',
                'https://www.bing.com/'
            ])
            
            # CRITICAL: Farklı format kombinasyonları
            format_choices = [
                'best[height<=720]/best[height<=480]/best',
                '22/18/136+140/137+140',  # 720p/360p/720p+audio/1080p+audio
                'bestvideo[height<=720]+bestaudio/best[height<=720]',
                'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst'  # Bazen düşük kalite daha az sorun
            ]
            
            # Rastgele ülke kodu
            country = random.choice(['US', 'TR', 'DE', 'FR', 'JP', 'CA', 'GB', 'NL', 'BR', 'IN'])
            
            print(f"🔄 YT-DLP Deneme {attempt+1}/{max_attempts}")
            print(f"   🌍 Ülke: {country}, 🕐 Bekle: {2**attempt}s")
            
            # yt-dlp komutu
            cmd = [
                'yt-dlp',
                '--no-cookies',
                '--no-check-certificate',
                '--geo-bypass',
                '--geo-bypass-country', country,
                '--user-agent', user_agent,
                '--referer', referer,
                '--sleep-interval', str(random.randint(2, 5)),
                '--max-sleep-interval', str(random.randint(5, 15)),
                '--retries', '15',  # Daha fazla retry
                '--fragment-retries', '15',
                '--skip-unavailable-fragments',
                '--no-warnings',
                '--quiet',
                '--format', random.choice(format_choices),
                '--output', output_file,
                '--force-ipv4',  # IPv4 zorla
                '--socket-timeout', '30',
                '--source-address', '0.0.0.0',  # Tüm IP'lerden bağlan
                youtube_url
            ]
            
            # Komutu çalıştır
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Dosya kontrolü
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    if file_size > 102400:  # 100KB'den büyük
                        print(f"✅ yt-dlp başarılı! ({file_size/1024/1024:.1f} MB)")
                        return True
                    else:
                        print(f"⚠️ Dosya çok küçük: {file_size} bytes")
                        os.remove(output_file)  # Sil ve tekrar dene
                else:
                    print("⚠️ Dosya oluşturulamadı")
            
            # Hata log'u
            if result.stderr:
                error_lines = [line for line in result.stderr.split('\n') if 'error' in line.lower()]
                if error_lines:
                    print(f"❌ Hata: {error_lines[0][:100]}")
            
        except subprocess.TimeoutExpired:
            print(f"⏱️ Timeout (Deneme {attempt+1})")
        except Exception as e:
            print(f"⚠️ Beklenmeyen hata: {str(e)[:100]}")
        
        # Exponential backoff beklemesi
        wait_time = (2 ** attempt) + random.uniform(1, 3)
        print(f"⏳ {wait_time:.1f} saniye bekleniyor...\n")
        time.sleep(wait_time)
    
    return False

# ============================================
# 2. KATMAN: TMDB FALLBACK (Görsel → Video)
# ============================================
def create_video_from_tmdb(tmdb_id, film_adi, duration, output_file):
    """TMDB'den görsel indir, video oluştur"""
    
    try:
        TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
        if not TMDB_KEY:
            return False
        
        print(f"🎨 TMDB Fallback: {film_adi}")
        
        # Film detaylarını al
        tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
        params = {'api_key': TMDB_KEY, 'language': 'tr-TR'}
        response = requests.get(tmdb_url, params=params, timeout=15)
        film_data = response.json()
        
        # Görsel URL
        image_url = None
        if film_data.get('backdrop_path'):
            image_url = f"https://image.tmdb.org/t/p/original{film_data['backdrop_path']}"
        elif film_data.get('poster_path'):
            image_url = f"https://image.tmdb.org/t/p/w500{film_data['poster_path']}"
        
        if not image_url:
            print("❌ Görsel bulunamadı")
            return False
        
        # Görseli indir
        img_file = f"temp_img_{tmdb_id}.jpg"
        img_response = requests.get(image_url, timeout=30)
        with open(img_file, 'wb') as f:
            f.write(img_response.content)
        
        # Video oluştur
        print("🔨 Görselden video render ediliyor...")
        
        # Filmin yılı
        year = film_data.get('release_date', '')[:4] if film_data.get('release_date') else ''
        title_text = f"{film_adi} ({year})" if year else film_adi
        
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', img_file,
            '-vf', f"scale=1280:720:force_original_aspect_ratio=decrease,"
                   f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                   f"zoompan=z='min(zoom+0.001,1.3)':d={int(duration*25)}:s=1280x720,"
                   f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
                   f"text='{title_text}':fontcolor=white:fontsize=36:"
                   f"box=1:boxcolor=black@0.6:boxborderw=10:"
                   f"x=(w-text_w)/2:y=h-120",
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
            print(f"✅ Fallback video oluşturuldu ({file_size/1024/1024:.1f} MB)")
            return True
        else:
            print(f"❌ Fallback hatası: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ TMDB Fallback hatası: {str(e)[:100]}")
        return False

# ============================================
# YARDIMCI FONKSİYONLAR
# ============================================
def get_youtube_url_from_tmdb(tmdb_id, api_key):
    """TMDB'den YouTube URL'sini al"""
    try:
        tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
        params = {'api_key': api_key, 'language': 'tr-TR'}
        response = requests.get(tmdb_url, params=params, timeout=15)
        data = response.json()
        
        # Önce trailer, sonra teaser, sonra herhangi bir video
        for video_type in ['Trailer', 'Teaser', 'Clip', 'Featurette']:
            for video in data.get('results', []):
                if video.get('site') == 'YouTube' and video.get('type') == video_type:
                    return f"https://www.youtube.com/watch?v={video['key']}"
        
        # Hiçbiri yoksa ilk YouTube videosu
        for video in data.get('results', []):
            if video.get('site') == 'YouTube':
                return f"https://www.youtube.com/watch?v={video['key']}"
                
    except Exception as e:
        print(f"⚠️ TMDB URL hatası: {e}")
    
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
            '-b:a', '192k',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Mix hatası: {e}")
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
        print("❌ TMDB_API_KEY bulunamadı!")
        sys.exit(1)
    
    print(f"🎬 Film: {film_adi}")
    print(f"🆔 Film ID: {film_id}, TMDB ID: {tmdb_id}")
    print("🚫 Cookie'siz 2-Katmanlı Sistem Aktif\n")
    
    # 1. YouTube URL'sini TMDB'den al
    print("🔍 TMDB'den YouTube URL'si aranıyor...")
    youtube_url = get_youtube_url_from_tmdb(tmdb_id, TMDB_KEY)
    
    if youtube_url:
        print(f"✅ YouTube URL bulundu: {youtube_url}")
    else:
        print("❌ YouTube URL bulunamadı, direkt Fallback'e geçilecek")
    
    # 2. TTS sesini indir
    print("\n🔊 TTS sesi indiriliyor...")
    mp3_file = f"ses_{film_id}.mp3"
    tts_duration = 180  # Varsayılan
    
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
        except:
            pass
            
        print(f"⏱️ TTS süresi: {tts_duration:.1f} saniye")
    except Exception as e:
        print(f"⚠️ TTS indirme hatası: {e}")
    
    # 3. YT-DLP İLE İNDİRME
    trailer_file = f"trailer_{film_id}.mp4"
    video_obtained = False
    
    if youtube_url:
        print("\n" + "="*50)
        print("1. KATMAN: GELİŞMİŞ YT-DLP")
        print("="*50)
        
        video_obtained = download_ytdlp_enhanced(youtube_url, trailer_file, max_attempts=5)
    
    # 4. FALLBACK
    if not video_obtained:
        print("\n" + "="*50)
        print("2. KATMAN: TMDB FALLBACK")
        print("="*50)
        
        video_obtained = create_video_from_tmdb(tmdb_id, film_adi, tts_duration, trailer_file)
    
    if not video_obtained:
        print("\n❌ TÜM YÖNTEMLER BAŞARISIZ!")
        sys.exit(1)
    
    # 5. SES VE VİDEOYU BİRLEŞTİR
    print("\n🔗 Video ve ses birleştiriliyor...")
    final_file = f"fragman_{film_id}.mp4"
    
    if mix_audio_video(trailer_file, mp3_file, final_file):
        file_size = os.path.getsize(final_file)
        print(f"✅ Birleştirme tamam: {final_file} ({file_size/1024/1024:.1f} MB)")
    else:
        print("❌ Birleştirme başarısız, sadece video kullanılıyor...")
        final_file = trailer_file
    
    # 6. CALLBACK
    print(f"\n📤 Callback'e gönderiliyor: {callback}")
    try:
        with open(final_file, 'rb') as video_file:
            files = {'video': (f'fragman_{film_id}.mp4', video_file, 'video/mp4')}
            data = {'film_id': film_id}
            
            response = requests.post(callback, files=files, data=data, timeout=180)
            print(f"📡 HTTP {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Callback başarılı!")
            else:
                print(f"⚠️ Callback hatası: {response.text[:200]}")
                
    except Exception as e:
        print(f"❌ Callback hatası: {e}")
    
    # 7. TEMİZLİK
    print("\n🧹 Temizlik yapılıyor...")
    for temp_file in [mp3_file, trailer_file]:
        if os.path.exists(temp_file) and temp_file != final_file:
            try:
                os.remove(temp_file)
            except:
                pass
    
    if os.path.exists(final_file) and final_file != trailer_file:
        try:
            os.remove(final_file)
        except:
            pass
    
    print("\n🎉 TAMAMLANDI!")

if __name__ == "__main__":
    main()
