#!/usr/bin/env python3
"""
fragman.py - 1+3+1 Otomatik Film İnceleme Sistemi
Gelişmiş ve Stabil Sürüm
"""

import os, json, requests, subprocess, time, sys, tempfile, random, logging, http.client
from datetime import datetime

# ============================================
# LOGLAMA AYARLARI
# ============================================
def setup_logging():
    """Detaylı loglama sistemini kur"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    log_filename = f"fragman_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

# ============================================
# 1. BASİT VE ÇALIŞAN KAPAK SİSTEMİ
# ============================================
def create_working_cover(tmdb_id, film_adi, cover_duration=5):
    """GÜVENİLİR kapak oluştur (basit ve çalışan)"""
    
    logger.info(f"🎨 Kapak oluşturuluyor: {film_adi}")
    
    cover_file = f"cover_{tmdb_id}.mp4"
    
    try:
        # Sadece film adı ve temel bilgilerle basit kapak
        font_path = "assets/font.ttf"
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if not os.path.exists(font_path):
                font_path = "Arial"
        
        # 1. Siyah arka plan
        # 2. Film adı büyük
        # 3. "İNCELEME" altında
        # 4. Kırmızı çizgi efekti
        
        filter_complex = (
            f"color=c=black:s=1920x1080:d={cover_duration}[bg];"
            f"[bg]drawtext=fontfile='{font_path}':text='{film_adi}':"
            f"fontcolor=white:fontsize=96:x=(w-text_w)/2:y=(h-text_h)/2-80,"
            f"drawtext=fontfile='{font_path}':text='İ N C E L E M E':"
            f"fontcolor=#40E0D0:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2+40,"
            f"drawbox=x=(w-300)/2:y=(h-text_h)/2+100:w=300:h=4:color=#40E0D0:t=fill,"
            f"fade=t=in:st=0:d=0.5,fade=t=out:st={cover_duration-0.5}:d=0.5"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s=1920x1080:d={cover_duration}',
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-vf', filter_complex,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-c:a', 'aac', '-b:a', '128k',
            '-t', str(cover_duration),
            cover_file
        ]
        
        logger.info(f"🎬 FFmpeg kapak oluşturuyor")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            if os.path.exists(cover_file):
                file_size = os.path.getsize(cover_file)
                logger.info(f"✅ Kapak oluşturuldu: {cover_file} ({file_size/1024:.1f} KB)")
                return cover_file
            else:
                logger.error("❌ Kapak dosyası oluşturulamadı")
        else:
            logger.error(f"❌ FFmpeg hatası: {result.stderr[:500]}")
            
    except Exception as e:
        logger.error(f"❌ Kapak oluşturma hatası: {str(e)}", exc_info=True)
    
    # Daha da basit fallback
    return create_minimal_cover(film_adi, cover_file)

def create_minimal_cover(film_adi, output_file, duration=5):
    """Minimal kapak (kesin çalışan)"""
    try:
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s=1280x720:d={duration}',
            '-vf', f"drawtext=text='{film_adi}':fontcolor=white:fontsize=72:"
                   f"x=(w-text_w)/2:y=(h-text_h)/2",
            '-c:v', 'libx264', '-t', str(duration),
            output_file
        ]
        subprocess.run(cmd, check=True, timeout=30, capture_output=True)
        logger.info(f"✅ Minimal kapak oluşturuldu: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"❌ Minimal kapak hatası: {e}")
        return None

# ============================================
# 2. İNDİRME SİSTEMLERİ
# ============================================
def download_ytdlp_enhanced(youtube_url, output_file, max_attempts=2):
    """YT-DLP ile indirme"""
    
    logger.info(f"🔗 YT-DLP başlatıldı: {youtube_url}")
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"🔄 YT-DLP Deneme {attempt+1}/{max_attempts}")
            
            cmd = [
                'yt-dlp',
                '-f', 'best[height<=720]',
                '-o', output_file,
                '--quiet',
                '--no-warnings',
                youtube_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0 and os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                if file_size > 1024000:
                    logger.info(f"✅ yt-dlp ile indirildi! ({file_size/1024/1024:.1f} MB)")
                    return True
                else:
                    logger.warning(f"⚠️ Dosya çok küçük: {file_size} bytes")
                    os.remove(output_file)
                        
        except Exception as e:
            logger.error(f"❌ YT-DLP hatası: {str(e)}")
        
        if attempt < max_attempts - 1:
            time.sleep(5)
    
    logger.error("❌ YT-DLP başarısız")
    return False

def get_rapidapi_keys():
    """RapidAPI key'lerini al"""
    keys = []
    
    # Yeni format: RAPIDAPI_KEY_1, RAPIDAPI_KEY_2
    for i in range(1, 6):
        key_name = f"RAPIDAPI_KEY_{i}"
        key_value = os.environ.get(key_name)
        if key_value:
            key_value = key_value.strip()
            if key_value and key_value not in keys:
                keys.append(key_value)
                logger.info(f"🔑 {key_name} bulundu: {key_value[:8]}...")
    
    # Eski format: RAPIDAPI_KEYS
    old_keys = os.environ.get("RAPIDAPI_KEYS", "")
    if old_keys:
        for key in old_keys.split(','):
            key = key.strip()
            if key and key not in keys:
                keys.append(key)
                logger.info(f"🔑 Eski format RapidAPI Key: {key[:8]}...")
    
    logger.info(f"📊 Toplam {len(keys)} RapidAPI anahtarı")
    return keys

def download_via_rapidapi_fast(youtube_id, output_file):
    """RapidAPI FAST ile indir (çalışan endpoint)"""
    
    rapidapi_keys = get_rapidapi_keys()
    if not rapidapi_keys:
        logger.warning("⚠️ RapidAPI key yok")
        return False
    
    api_endpoint = "youtube-video-fast-downloader-24-7.p.rapidapi.com"
    api_path = f"/download_video/{youtube_id}?quality=247"
    
    for api_key in rapidapi_keys:
        try:
            logger.info(f"🔑 RapidAPI deneniyor: {api_key[:8]}...")
            
            conn = http.client.HTTPSConnection(api_endpoint)
            headers = {
                'x-rapidapi-key': api_key,
                'x-rapidapi-host': api_endpoint
            }
            
            conn.request("GET", api_path, headers=headers)
            res = conn.getresponse()
            
            if res.status == 200:
                data = res.read().decode("utf-8")
                video_info = json.loads(data)
                
                logger.info(f"✅ API yanıt aldı: {video_info.get('size', 0)} bytes")
                
                # Video URL'lerini al
                video_url = video_info.get('file')
                reserved_url = video_info.get('reserved_file', video_url)
                
                # Video hazır olana kadar bekle (maks 300 sn)
                for wait_seconds in range(0, 300, 30):
                    for url in [video_url, reserved_url]:
                        try:
                            logger.info(f"⏱️ Kontrol {wait_seconds}/300 sn: {url[:60]}...")
                            
                            # HEAD isteği ile hazır mı kontrol et
                            head_response = requests.head(url, timeout=10, allow_redirects=True)
                            if head_response.status_code == 200:
                                content_length = head_response.headers.get('content-length')
                                if content_length and int(content_length) > 1000000:
                                    logger.info(f"✅ Video hazır! {int(content_length)/1024/1024:.1f} MB")
                                    
                                    # Videoyu indir
                                    logger.info("📥 Video indiriliyor...")
                                    video_response = requests.get(url, stream=True, timeout=120)
                                    
                                    with open(output_file, 'wb') as f:
                                        for chunk in video_response.iter_content(chunk_size=8192):
                                            f.write(chunk)
                                    
                                    if os.path.exists(output_file):
                                        file_size = os.path.getsize(output_file)
                                        if file_size > 1000000:
                                            logger.info(f"✅ RapidAPI ile indirildi! {file_size/1024/1024:.1f} MB")
                                            return True
                                        else:
                                            logger.warning(f"⚠️ Dosya çok küçük: {file_size} bytes")
                                            os.remove(output_file)
                                            break
                                break
                            elif head_response.status_code == 404:
                                logger.info(f"⏳ Video hazır değil, 30 sn bekleniyor...")
                                time.sleep(30)
                                break
                                
                        except Exception as e:
                            logger.warning(f"⚠️ URL kontrol hatası: {str(e)[:100]}")
                            time.sleep(30)
                
                logger.warning(f"⚠️ Bu key ile video hazırlanamadı: {api_key[:8]}...")
                    
            elif res.status == 403:
                logger.warning(f"⚠️ API'ye abone değilsiniz: {api_key[:8]}...")
            elif res.status == 429:
                logger.warning(f"⚠️ Rate limit: {api_key[:8]}...")
            else:
                logger.warning(f"⚠️ HTTP {res.status}: {api_key[:8]}...")
                
        except Exception as e:
            logger.error(f"❌ RapidAPI hatası: {str(e)[:100]}")
        
        # Diğer key için bekle
        time.sleep(2)
    
    logger.error("❌ Tüm RapidAPI key'leri başarısız")
    return False

def download_via_pytube(youtube_url, output_file):
    """Pytube ile indirme"""
    try:
        logger.info(f"🐍 Pytube deneniyor: {youtube_url}")
        
        from pytube import YouTube
        yt = YouTube(youtube_url)
        
        stream = yt.streams.filter(
            progressive=True, 
            file_extension='mp4'
        ).order_by('resolution').desc().first()
        
        if stream:
            logger.info(f"📦 Stream bulundu: {stream.resolution}")
            stream.download(filename=output_file)
            
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                if file_size > 1024000:
                    logger.info(f"✅ Pytube ile indirildi! {file_size/1024/1024:.1f} MB")
                    return True
        
        logger.error("❌ Pytube stream bulunamadı")
        return False
        
    except Exception as e:
        logger.error(f"❌ Pytube hatası: {str(e)}")
        return False

# ============================================
# 3. YARDIMCI FONKSİYONLAR
# ============================================
def extract_video_id(url):
    """YouTube ID çıkar"""
    if not url: 
        return None
    
    import re
    patterns = [
        r'(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/(?:.*?&)?v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return url.split('/')[-1]

def get_youtube_url_from_tmdb(tmdb_id, api_key):
    """TMDB'den YouTube URL al"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
        params = {'api_key': api_key, 'language': 'tr-TR'}
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        for video in data.get('results', []):
            if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
                video_url = f"https://www.youtube.com/watch?v={video['key']}"
                logger.info(f"✅ TMDB fragman bulundu: {video['name']}")
                return video_url
        
        for video in data.get('results', []):
            if video.get('site') == 'YouTube':
                video_url = f"https://www.youtube.com/watch?v={video['key']}"
                logger.info(f"✅ TMDB video bulundu: {video['name']}")
                return video_url
                
    except Exception as e:
        logger.error(f"❌ TMDB video hatası: {str(e)}")
    
    return None

def get_tts_duration(tts_url):
    """TTS süresi al"""
    try:
        logger.info(f"🔊 TTS süresi alınıyor: {tts_url}")
        
        tts_temp = "temp_tts.mp3"
        response = requests.get(tts_url, timeout=30)
        with open(tts_temp, 'wb') as f:
            f.write(response.content)
        
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 
               'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', tts_temp]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        os.remove(tts_temp)
        
        if result.returncode == 0 and result.stdout.strip():
            duration = float(result.stdout.strip())
            logger.info(f"⏱️ TTS süresi: {duration:.1f} saniye")
            return duration
            
    except Exception as e:
        logger.error(f"⚠️ TTS süresi alınamadı: {e}")
    
    return 180

# ============================================
# 4. 3 KATMANLI İÇERİK SİSTEMİ
# ============================================
def get_main_content_via_3layer(youtube_url, tmdb_id, film_adi, duration, output_file):
    """3 katmanla içerik al"""
    
    youtube_id = extract_video_id(youtube_url) if youtube_url else None
    
    # KATMAN 1: RapidAPI (EN GÜVENİLİR)
    logger.info("="*50)
    logger.info("KATMAN 1: RapidAPI (FAST)")
    logger.info("="*50)
    
    if youtube_id:
        if download_via_rapidapi_fast(youtube_id, output_file):
            return True
    
    # KATMAN 2: YT-DLP
    logger.info("="*50)
    logger.info("KATMAN 2: YT-DLP")
    logger.info("="*50)
    
    if youtube_url:
        if download_ytdlp_enhanced(youtube_url, output_file):
            return True
    
    # KATMAN 3: Pytube
    logger.info("="*50)
    logger.info("KATMAN 3: Pytube")
    logger.info("="*50)
    
    if youtube_url:
        if download_via_pytube(youtube_url, output_file):
            return True
    
    # KATMAN 4: Fallback (siyah ekran)
    logger.info("="*50)
    logger.info("KATMAN 4: Fallback İçerik")
    logger.info("="*50)
    
    return create_fallback_content(film_adi, duration, output_file)

def create_fallback_content(film_adi, duration, output_file):
    """Fallback içerik (siyah ekran)"""
    try:
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s=1280x720:d={duration}',
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-vf', f"drawtext=text='{film_adi}':fontcolor=white:fontsize=48:"
                   f"x=(w-text_w)/2:y=(h-text_h)/2",
            '-c:v', 'libx264', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '128k',
            '-t', str(duration),
            output_file
        ]
        
        subprocess.run(cmd, check=True, timeout=60, capture_output=True)
        logger.info(f"✅ Fallback içerik oluşturuldu: {output_file}")
        return True
    except Exception as e:
        logger.error(f"❌ Fallback içerik hatası: {e}")
        return False

# ============================================
# 5. GÜVENLİ BİRLEŞTİRME
# ============================================
def combine_cover_and_content_safely(cover_path, content_path, output_path):
    """GÜVENLİ birleştirme (format uyumluluğu sağlanarak)"""
    
    try:
        if not os.path.exists(cover_path):
            logger.error(f"❌ Kapak yok: {cover_path}")
            return False
        if not os.path.exists(content_path):
            logger.error(f"❌ İçerik yok: {content_path}")
            return False
        
        logger.info("🔗 Güvenli birleştirme başlatıldı")
        
        # 1. İçeriğin formatını al
        cmd_info = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,codec_name',
            '-of', 'csv=p=0', content_path
        ]
        
        result = subprocess.run(cmd_info, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"❌ İçerik bilgisi alınamadı")
            return False
        
        info_parts = result.stdout.strip().split(',')
        if len(info_parts) >= 3:
            target_width = info_parts[0]
            target_height = info_parts[1]
            target_fps = info_parts[2].split('/')[0]
            logger.info(f"🎯 Hedef format: {target_width}x{target_height}, {target_fps} fps")
        else:
            # Varsayılan format
            target_width = "1280"
            target_height = "720"
            target_fps = "24"
            logger.info(f"🎯 Varsayılan format: {target_width}x{target_height}, {target_fps} fps")
        
        # 2. Kapağı hedef formata dönüştür
        converted_cover = "converted_cover.mp4"
        cmd_convert = [
            'ffmpeg', '-y',
            '-i', cover_path,
            '-vf', f'scale={target_width}:{target_height},fps={target_fps}',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-t', '5',  # Kapak süresi 5 saniye
            converted_cover
        ]
        
        logger.info(f"🔄 Kapak dönüştürülüyor")
        result_convert = subprocess.run(cmd_convert, capture_output=True, text=True, timeout=60)
        if result_convert.returncode != 0:
            logger.error(f"❌ Kapak dönüştürme hatası: {result_convert.stderr[:500]}")
            return False
        
        # 3. Concat listesi oluştur
        list_file = "concat_list.txt"
        with open(list_file, 'w') as f:
            f.write(f"file '{os.path.abspath(converted_cover)}'\n")
            f.write(f"file '{os.path.abspath(content_path)}'\n")
        
        # 4. Birleştir
        cmd_concat = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            '-movflags', '+faststart',
            output_path
        ]
        
        logger.info("🔗 Videolar birleştiriliyor...")
        result_concat = subprocess.run(cmd_concat, capture_output=True, text=True, timeout=180)
        
        # Temizlik
        for temp_file in [converted_cover, list_file]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        if result_concat.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"✅ Birleştirme tamamlandı! {file_size/1024/1024:.1f} MB")
            return True
        else:
            logger.error(f"❌ Birleştirme hatası: {result_concat.stderr[:500]}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Birleştirme hatası: {e}", exc_info=True)
        return False

# ============================================
# 6. TTS EKLEME
# ============================================
def add_tts_to_video_safely(video_path, tts_url, output_path):
    """TTS ekle"""
    try:
        logger.info(f"🔊 TTS ekleniyor: {tts_url}")
        
        # TTS indir
        tts_file = "tts_temp.mp3"
        response = requests.get(tts_url, timeout=30)
        with open(tts_file, 'wb') as f:
            f.write(response.content)
        
        # TTS'yi videoya ekle
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', tts_file,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_path
        ]
        
        subprocess.run(cmd, check=True, timeout=180, capture_output=True)
        os.remove(tts_file)
        
        logger.info(f"✅ TTS eklendi: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ TTS ekleme hatası: {e}")
        if os.path.exists("tts_temp.mp3"):
            os.remove("tts_temp.mp3")
        return False

# ============================================
# 7. ANA İŞ AKIŞI
# ============================================
def main():
    logger.info("="*60)
    logger.info("🚀 1+3+1 OTOMATİK SİSTEM")
    logger.info("="*60)
    
    try:
        # GitHub event verilerini al
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path or not os.path.exists(event_path):
            logger.warning("❌ GITHUB_EVENT_PATH yok, test modu...")
            p = {
                "film_id": "test_001",
                "tmdb_id": "1234731",
                "film_adi": "Anakonda",
                "ses_url": "https://prodopsy.com/youtube/audio/ses_2.mp3",
                "callback": "https://webhook.site/test"
            }
        else:
            event = json.load(open(event_path, encoding="utf-8"))
            p = event["client_payload"]
        
        film_id = p["film_id"]
        tmdb_id = p["tmdb_id"]
        film_adi = p["film_adi"]
        ses_url = p["ses_url"]
        callback = p["callback"]
        
        logger.info(f"🎬 Film: {film_adi}")
        logger.info(f"🎯 Film ID: {film_id}")
        logger.info(f"📊 TMDB ID: {tmdb_id}")
        
        # ADIM 1: KAPAK OLUŞTUR
        logger.info("\n" + "="*60)
        logger.info("ADIM 1: KAPAK OLUŞTURMA")
        logger.info("="*60)
        
        cover_file = create_working_cover(tmdb_id, film_adi)
        if not cover_file:
            logger.error("❌ Kapak oluşturulamadı")
            return False
        
        # ADIM 2: İÇERİK AL
        logger.info("\n" + "="*60)
        logger.info("ADIM 2: 3 KATMANLI İÇERİK")
        logger.info("="*60)
        
        TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
        youtube_url = None
        
        if TMDB_KEY:
            youtube_url = get_youtube_url_from_tmdb(tmdb_id, TMDB_KEY)
            if youtube_url:
                logger.info(f"🔗 YouTube URL: {youtube_url}")
        
        tts_duration = get_tts_duration(ses_url)
        content_file = f"content_{film_id}.mp4"
        
        if not get_main_content_via_3layer(youtube_url, tmdb_id, film_adi, tts_duration, content_file):
            logger.error("❌ İçerik alınamadı")
            return False
        
        # ADIM 3: BİRLEŞTİR ve TTS EKLE
        logger.info("\n" + "="*60)
        logger.info("ADIM 3: BİRLEŞTİRME ve TTS")
        logger.info("="*60)
        
        combined_file = f"combined_{film_id}.mp4"
        if not combine_cover_and_content_safely(cover_file, content_file, combined_file):
            logger.warning("⚠️ Birleştirme başarısız, sadece içerik")
            combined_file = content_file
        
        final_file = f"final_{film_id}.mp4"
        if not add_tts_to_video_safely(combined_file, ses_url, final_file):
            logger.warning("⚠️ TTS eklenemedi")
            final_file = combined_file
        
        # ADIM 4: CALLBACK
        logger.info("\n" + "="*60)
        logger.info("ADIM 4: CALLBACK")
        logger.info("="*60)
        
        try:
            if os.path.exists(final_file):
                file_size = os.path.getsize(final_file) / (1024*1024)
                logger.info(f"📦 Video hazır: {file_size:.1f} MB")
                
                with open(final_file, 'rb') as f:
                    files = {'video': (f'fragman_{film_id}.mp4', f, 'video/mp4')}
                    data = {'film_id': film_id, 'status': 'success'}
                    response = requests.post(callback, files=files, data=data, timeout=180)
                    
                    logger.info(f"📡 Callback durumu: {response.status_code}")
                    if response.status_code == 200:
                        logger.info("✅ Callback başarılı!")
                    else:
                        logger.error(f"❌ Callback hatası: {response.text[:200]}")
            else:
                logger.error("❌ Final video bulunamadı")
                
        except Exception as e:
            logger.error(f"❌ Callback hatası: {e}")
        
        # TEMİZLİK
        logger.info("\n🧹 Temizlik...")
        for temp_file in [cover_file, content_file, combined_file, final_file]:
            if temp_file and os.path.exists(temp_file):
                try:
                    if temp_file != final_file:
                        os.remove(temp_file)
                except:
                    pass
        
        logger.info("\n" + "="*60)
        logger.info("✅ SİSTEM TAMAMLANDI!")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ana hata: {e}", exc_info=True)
        return False

# ============================================
# ÇALIŞTIR
# ============================================
if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.error("⏹️ Durduruldu")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Beklenmeyen hata: {e}")
        sys.exit(1)
