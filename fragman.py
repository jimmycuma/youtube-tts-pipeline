#!/usr/bin/env python3
"""
fragman.py - Düzeltilmiş versiyon
"""

import os, json, requests, subprocess, time, random, sys

# ============================================
# YT-DLP DOWNLOAD (GÜNCELLENMİŞ)
# ============================================
def download_ytdlp_enhanced(youtube_url, output_file, max_attempts=3):
    """Gelişmiş yt-dlp ile YouTube videosu indir"""
    
    for attempt in range(max_attempts):
        try:
            print(f"🔄 YT-DLP Deneme {attempt+1}/{max_attempts}")
            
            # İki yöntem deneyelim: 1. yt-dlp binary, 2. python module
            try:
                # Önce yt-dlp binary kullan
                cmd = [
                    'yt-dlp',
                    '--no-cookies',
                    '--geo-bypass',
                    '--retries', '5',
                    '--fragment-retries', '5',
                    '--socket-timeout', '30',
                    '-f', 'best[height<=720]/best[height<=480]',
                    '-o', output_file,
                    '--quiet',
                    youtube_url
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
            except FileNotFoundError:
                # Binary yoksa python module kullan
                print("⚠️ yt-dlp binary bulunamadı, Python module deneniyor...")
                import yt_dlp
                
                ydl_opts = {
                    'format': 'best[height<=720]/best[height<=480]',
                    'outtmpl': output_file,
                    'quiet': True,
                    'no_warnings': True,
                    'ignoreerrors': True,
                    'retries': 5,
                    'fragment_retries': 5,
                    'socket_timeout': 30,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])
            
            # Dosya kontrolü
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                if file_size > 102400:  # 100KB'den büyük
                    print(f"✅ YouTube'dan indirildi! ({file_size/1024/1024:.1f} MB)")
                    return True
                else:
                    print(f"⚠️ Dosya çok küçük: {file_size} bytes")
                    os.remove(output_file)
                    
        except Exception as e:
            print(f"❌ YT-DLP hatası: {str(e)[:100]}")
        
        if attempt < max_attempts - 1:
            wait_time = (attempt + 1) * 5
            print(f"⏳ {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
    
    return False

# ============================================
# ANA PROGRAM (DÜZENLENMİŞ)
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
    
    print(f"🎬 Film: {film_adi}")
    print(f"🆔 Film ID: {film_id}, TMDB ID: {tmdb_id}")
    
    # 1. TTS SESİNİ İNDİR (RETRY'LERLE)
    print("\n🔊 TTS sesi indiriliyor...")
    mp3_file = f"ses_{film_id}.mp3"
    tts_duration = 180
    
    if download_tts_with_retry(ses_url, mp3_file):
        # Süreyi ölç
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
    else:
        print("⚠️ TTS indirilemedi, video oluşturulacak...")
        mp3_file = None
    
    # 2. YOUTUBE URL'SİNİ AL
    TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
    youtube_url = None
    
    if TMDB_KEY:
        try:
            tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
            params = {'api_key': TMDB_KEY, 'language': 'tr-TR'}
            response = requests.get(tmdb_url, params=params, timeout=15)
            data = response.json()
            
            for video in data.get('results', []):
                if video.get('site') == 'YouTube':
                    youtube_url = f"https://www.youtube.com/watch?v={video['key']}"
                    print(f"✅ YouTube URL: {youtube_url}")
                    break
        except:
            pass
    
    # 3. YOUTUBE İNDİR VEYA FALLBACK
    trailer_file = f"trailer_{film_id}.mp4"
    video_obtained = False
    
    if youtube_url:
        print("\n" + "="*50)
        print("YT-DLP İLE İNDİRME")
        print("="*50)
        video_obtained = download_ytdlp_enhanced(youtube_url, trailer_file)
    
    # 4. FALLBACK
    if not video_obtained and TMDB_KEY:
        print("\n" + "="*50)
        print("TMDB FALLBACK")
        print("="*50)
        
        # Basit fallback - sadece siyah video
        try:
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'color=c=black:s=1280x720:d={tts_duration}:r=25',
                '-vf', f"drawtext=text='{film_adi}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                trailer_file
            ]
            subprocess.run(cmd, check=True, timeout=60)
            video_obtained = True
            print("✅ Fallback video oluşturuldu")
        except:
            pass
    
    if not video_obtained:
        print("❌ Video oluşturulamadı!")
        sys.exit(1)
    
    # 5. VİDEOYU HAZIRLA
    final_file = trailer_file
    
    # Eğer TTS varsa birleştir
    if mp3_file and os.path.exists(mp3_file):
        print("\n🔗 Video ve ses birleştiriliyor...")
        final_file = f"fragman_{film_id}.mp4"
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', trailer_file,
                '-i', mp3_file,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                final_file
            ]
            subprocess.run(cmd, check=True, timeout=300)
            print("✅ Ses ve video birleştirildi")
        except:
            final_file = trailer_file
            print("⚠️ Birleştirme başarısız, sadece video")
    
    # 6. CALLBACK GÖNDER
    if send_callback_with_fallback(callback, film_id, final_file):
        print("✅ İşlem başarıyla tamamlandı!")
    else:
        print("⚠️ Callback başarısız ama işlem tamam")
    
    # 7. TEMİZLİK
    for temp_file in [mp3_file, trailer_file]:
        if temp_file and os.path.exists(temp_file) and temp_file != final_file:
            try:
                os.remove(temp_file)
            except:
                pass

if __name__ == "__main__":
    main()
