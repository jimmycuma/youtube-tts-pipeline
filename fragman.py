#!/usr/bin/env python3
"""
fragman.py - 1+3+1 Otomatik Film İnceleme Sistemi
Gelişmiş Loglama ve Çoklu İndirme Sistemi
"""

import os, json, requests, subprocess, time, sys, tempfile, random, logging
from datetime import datetime

# ============================================
# LOGLAMA AYARLARI
# ============================================
def setup_logging():
    """Detaylı loglama sistemini kur"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Konsol log handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # Dosya log handler
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
# 1. SİNEMATİK KAPAK OLUŞTURMA
# ============================================
def create_unified_cover(tmdb_id, film_adi, cover_duration=5):
    """TMDB görselleriyle sinematik kapak oluştur."""
    
    logger.info(f"🎨 Sinematik kapak oluşturuluyor: {film_adi}")
    
    TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
    if not TMDB_KEY:
        logger.warning("⚠️ TMDB_API_KEY bulunamadı. Basit kapak kullanılacak.")
        return create_simple_cover(film_adi, f"cover_{tmdb_id}.mp4")
    
    temp_files = []
    cover_file = f"cover_{tmdb_id}.mp4"
    
    try:
        # TMDB'den film detaylarını al
        logger.info(f"📡 TMDB API çağrısı: https://api.themoviedb.org/3/movie/{tmdb_id}")
        tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
        params = {'api_key': TMDB_KEY, 'language': 'tr-TR', 'append_to_response': 'images'}
        response = requests.get(tmdb_url, params=params, timeout=15)
        logger.info(f"📡 TMDB Response Status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"❌ TMDB API hatası: {response.status_code}")
            return create_simple_cover(film_adi, cover_file)
        
        film_data = response.json()
        logger.info(f"✅ TMDB Data alındı: {film_data.get('title', 'Bilinmeyen')}")
        
        # Görselleri seç
        backdrop_path = film_data.get('backdrop_path')
        poster_path = film_data.get('poster_path')
        
        logger.info(f"🖼️ Backdrop Path: {backdrop_path}")
        logger.info(f"🖼️ Poster Path: {poster_path}")
        
        if not backdrop_path and film_data.get('images', {}).get('backdrops'):
            backdrop_path = film_data['images']['backdrops'][0]['file_path']
            logger.info(f"🔄 Alternatif Backdrop: {backdrop_path}")
        
        if not poster_path and film_data.get('images', {}).get('posters'):
            poster_path = film_data['images']['posters'][0]['file_path']
            logger.info(f"🔄 Alternatif Poster: {poster_path}")
        
        # Görselleri indir
        base_url = "https://image.tmdb.org/t/p/original"
        
        backdrop_file = None
        poster_file = None
        
        if backdrop_path:
            backdrop_url = f"{base_url}{backdrop_path}"
            backdrop_file = f"backdrop_{tmdb_id}.jpg"
            logger.info(f"📥 Backdrop indiriliyor: {backdrop_url}")
            
            with open(backdrop_file, 'wb') as f:
                f.write(requests.get(backdrop_url, timeout=20).content)
            temp_files.append(backdrop_file)
            file_size = os.path.getsize(backdrop_file)
            logger.info(f"✅ Backdrop indirildi: {file_size/1024:.1f} KB")
        
        if poster_path:
            poster_url = f"{base_url}{poster_path}"
            poster_file = f"poster_{tmdb_id}.jpg"
            logger.info(f"📥 Poster indiriliyor: {poster_url}")
            
            with open(poster_file, 'wb') as f:
                f.write(requests.get(poster_url, timeout=20).content)
            temp_files.append(poster_file)
            file_size = os.path.getsize(poster_file)
            logger.info(f"✅ Poster indirildi: {file_size/1024:.1f} KB")
        
        # Film bilgileri
        year = film_data.get('release_date', '')[:4] if film_data.get('release_date') else ''
        title_display = f"{film_adi} ({year})" if year else film_adi
        
        # FFmpeg komutu - SİNEMATİK KAPAK
        font_path = "assets/font.ttf"
        if not os.path.exists(font_path):
            logger.warning(f"⚠️ Font bulunamadı: {font_path}, sistem fontu kullanılacak")
            font_path = "Arial"
        
        filter_parts = []
        
        # Backdrop işleme
        if backdrop_file:
            filter_parts.append(
                f"movie={backdrop_file},scale=1920:1080,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
                f"colorchannelmixer=aa=0.6,"
                f"zoompan=z='1.00':d={cover_duration*25}[bg]"
            )
        else:
            filter_parts.append(f"color=c=black:s=1920x1080:d={cover_duration}[bg]")
        
        # Poster ekleme
        if poster_file:
            filter_parts.append(
                f"movie={poster_file},scale=400:-1[poster];"
                f"[bg][poster]overlay=x=W-w-80:y=(H-h)/2[bg_with_poster]"
            )
            bg_layer = "bg_with_poster"
        else:
            bg_layer = "bg"
        
        # Film adı
        filter_parts.append(
            f"[{bg_layer}]drawtext=fontfile='{font_path}':"
            f"text='{title_display}':fontcolor=white:fontsize=86:"
            f"borderw=4:bordercolor=black@0.8:"
            f"x=(w-text_w)/2:y=(h-text_h)/2-50:"
            f"alpha='if(lt(t,1),0,if(lt(t,2),(t-1)/1,1))'[with_title]"
        )
        
        # "İNCELEME" yazısı
        filter_parts.append(
            f"[with_title]drawtext=fontfile='{font_path}':"
            f"text='İ N C E L E M E':fontcolor=#40E0D0:fontsize=42:"
            f"borderw=2:bordercolor=black@0.6:"
            f"x=(w-text_w)/2:y=(h-text_h)/2+60[with_subtitle];"
            f"[with_subtitle]drawbox=x=(w-180)/2:y=(h-text_h)/2+110:"
            f"w=180:h=3:color=#40E0D0:t=fill[final]"
        )
        
        # Grain efekti
        filter_parts.append(
            f"[final]noise=c0s=8:allf=t[grainy];"
            f"[grainy]fade=t=in:st=0:d=1,fade=t=out:st={cover_duration-1}:d=1[output]"
        )
        
        filter_complex = ";".join(filter_parts)
        logger.debug(f"🔧 FFmpeg Filter Complex: {filter_complex[:300]}...")
        
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-filter_complex', filter_complex,
            '-map', '[output]',
            '-map', '0:a',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
            '-c:a', 'aac', '-b:a', '128k',
            '-t', str(cover_duration), '-r', '25',
            cover_file
        ]
        
        logger.info(f"🎬 FFmpeg kapak oluşturuyor: {cover_file}")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
        
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
    
    finally:
        # Temizlik
        logger.info("🧹 Kapak geçici dosyaları temizleniyor...")
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    logger.debug(f"✅ Geçici dosya silindi: {f}")
                except:
                    logger.warning(f"⚠️ Geçici dosya silinemedi: {f}")
    
    # Fallback: Basit kapak
    logger.info("🔄 Fallback: Basit kapak oluşturuluyor")
    return create_simple_cover(film_adi, cover_file)

def create_simple_cover(film_adi, output_file, duration=5):
    """Basit siyah kapak oluştur (fallback)."""
    try:
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s=1920x1080:d={duration}',
            '-vf', f"drawtext=text='{film_adi}':fontcolor=white:fontsize=72:"
                   f"x=(w-text_w)/2:y=(h-text_h)/2",
            '-c:v', 'libx264', '-t', str(duration),
            output_file
        ]
        logger.info(f"🎬 Basit kapak oluşturuluyor")
        subprocess.run(cmd, check=True, timeout=30)
        logger.info(f"✅ Basit kapak oluşturuldu: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"❌ Basit kapak hatası: {e}", exc_info=True)
        return None

# ============================================
# 2. İNDİRME SİSTEMLERİ
# ============================================
def download_ytdlp_enhanced(youtube_url, output_file, max_attempts=3):
    """Gelişmiş yt-dlp ile YouTube videosu indir"""
    
    logger.info(f"🔗 YT-DLP başlatıldı: {youtube_url}")
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"🔄 YT-DLP Deneme {attempt+1}/{max_attempts}")
            
            # Agresif yt-dlp ayarları
            cmd = [
                'yt-dlp',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--referer', 'https://www.youtube.com/',
                '--socket-timeout', '60',
                '--retries', '10',
                '--fragment-retries', '10',
                '--throttled-rate', '100K',
                '--no-check-certificate',
                '--geo-bypass',
                '--geo-bypass-country', 'US',
                '--extractor-args', 'youtube:player_client=android',
                '--format', 'best[height<=720]/best[height<=480]/best',
                '--output', output_file,
                '--verbose',
                '--force-ipv4',
                youtube_url
            ]
            
            logger.debug(f"🤖 YT-DLP komutu: {' '.join(cmd[:10])}...")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Log detayları
            if result.stdout:
                logger.debug(f"📄 YT-DLP stdout: {result.stdout[-500:]}")
            if result.stderr:
                logger.error(f"❌ YT-DLP stderr: {result.stderr[-500:]}")
            
            if result.returncode == 0:
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    if file_size > 1024000:  # 1MB'den büyük
                        logger.info(f"✅ yt-dlp ile indirildi! ({file_size/1024/1024:.1f} MB)")
                        return True
                    else:
                        logger.warning(f"⚠️ Dosya çok küçük: {file_size} bytes")
                        os.remove(output_file)
                else:
                    logger.error("⚠️ Çıktı dosyası oluşmadı")
            else:
                logger.error(f"❌ YT-DLP exit code: {result.returncode}")
                        
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ YT-DLP zaman aşımı (300 saniye)")
        except Exception as e:
            logger.error(f"❌ YT-DLP hatası: {str(e)}", exc_info=True)
        
        if attempt < max_attempts - 1:
            wait_time = (attempt + 1) * 10
            logger.info(f"⏳ {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
    
    logger.error("❌ YT-DLP ile indirme başarısız")
    return False

def download_via_rapidapi_direct(youtube_id, output_file):
    """Doğrudan RapidAPI ile video indir (yeni endpoint)"""
    
    rapidapi_keys = get_all_rapidapi_keys()
    
    if not rapidapi_keys:
        logger.warning("⚠️ Hiç RapidAPI key bulunamadı!")
        return False
    
    logger.info(f"🔑 {len(rapidapi_keys)} RapidAPI anahtarı ile deneniyor...")
    
    # API endpoint bilgileri
    api_endpoint = "youtube-video-fast-downloader-24-7.p.rapidapi.com"
    api_path = f"/download_video/{youtube_id}?quality=247"
    
    for i, api_key in enumerate(rapidapi_keys):
        try:
            logger.info(f"🔑 RapidAPI Key {i+1}/{len(rapidapi_keys)} deneniyor: {api_key[:8]}...")
            
            headers = {
                'x-rapidapi-key': api_key,
                'x-rapidapi-host': api_endpoint
            }
            
            import http.client
            
            conn = http.client.HTTPSConnection(api_endpoint)
            conn.request("GET", api_path, headers=headers)
            
            res = conn.getresponse()
            status_code = res.status
            logger.info(f"📡 RapidAPI Response: {status_code}")
            
            if status_code == 200:
                data = res.read().decode("utf-8")
                logger.info(f"✅ RapidAPI JSON yanıtı alındı")
                
                # JSON'u parse et
                try:
                    video_info = json.loads(data)
                    logger.info(f"📊 Video Bilgileri:")
                    logger.info(f"  - Boyut: {video_info.get('size', 'Bilinmiyor')} bytes")
                    logger.info(f"  - Bitrate: {video_info.get('bitrate', 'Bilinmiyor')}")
                    logger.info(f"  - Kalite: {video_info.get('quality', 'Bilinmiyor')}")
                    logger.info(f"  - Tür: {video_info.get('type', 'Bilinmiyor')}")
                    logger.info(f"  - Açıklama: {video_info.get('comment', 'Bilinmiyor')}")
                    
                    # Video URL'sini al
                    video_url = video_info.get('file')
                    reserved_url = video_info.get('reserved_file', video_url)
                    
                    if not video_url:
                        logger.error("❌ JSON'da video URL'si yok")
                        continue
                    
                    logger.info(f"🔗 Video URL: {video_url[:80]}...")
                    logger.info(f"🔗 Yedek URL: {reserved_url[:80]}...")
                    
                    # Video hazır olana kadar bekle
                    logger.info("⏳ Video hazırlanıyor bekleniyor (20-300 saniye)...")
                    
                    # URL'leri dene
                    urls_to_try = [video_url, reserved_url]
                    downloaded = False
                    
                    for url in urls_to_try:
                        if downloaded:
                            break
                            
                        logger.info(f"🔄 URL deneniyor: {url[:80]}...")
                        
                        # Video hazır olana kadar bekle (maksimum 320 saniye)
                        for wait_seconds in range(0, 320, 20):
                            try:
                                logger.info(f"⏱️ Kontrol {wait_seconds}/320 saniye...")
                                
                                # HEAD isteği ile hazır olup olmadığını kontrol et
                                head_response = requests.head(url, timeout=10, allow_redirects=True)
                                logger.debug(f"📡 HEAD Response: {head_response.status_code}")
                                
                                if head_response.status_code == 200:
                                    content_length = head_response.headers.get('content-length')
                                    if content_length and int(content_length) > 1000000:  # 1MB'den büyük
                                        logger.info(f"✅ Video hazır! Boyut: {int(content_length)/1024/1024:.1f} MB")
                                        
                                        # Videoyu indir
                                        logger.info("📥 Video indiriliyor...")
                                        video_response = requests.get(url, stream=True, timeout=60)
                                        
                                        with open(output_file, 'wb') as f:
                                            total_size = int(video_response.headers.get('content-length', 0))
                                            downloaded_size = 0
                                            
                                            for chunk in video_response.iter_content(chunk_size=8192):
                                                if chunk:
                                                    f.write(chunk)
                                                    downloaded_size += len(chunk)
                                                    
                                                    # İlerleme güncellemesi
                                                    if total_size > 0 and downloaded_size % (5 * 1024 * 1024) < 8192:
                                                        progress = (downloaded_size / total_size) * 100
                                                        logger.info(f"📊 İlerleme: {progress:.1f}% ({downloaded_size/1024/1024:.1f} MB)")
                                        
                                        # İndirme kontrolü
                                        if os.path.exists(output_file):
                                            file_size = os.path.getsize(output_file)
                                            logger.info(f"✅ İndirme tamamlandı! {file_size/1024/1024:.1f} MB")
                                            
                                            if file_size > 1000000:  # 1MB'den büyük
                                                logger.info(f"🎉 RapidAPI ile başarıyla indirildi!")
                                                logger.info(f"🔑 Kullanılan Key: {api_key[:8]}...")
                                                return True
                                            else:
                                                logger.warning(f"⚠️ Dosya çok küçük: {file_size} bytes")
                                                os.remove(output_file)
                                                break
                                    
                                    break
                                elif head_response.status_code == 404:
                                    # Henüz hazır değil
                                    logger.info(f"⏳ Video henüz hazır değil, {20} saniye bekleniyor...")
                                    time.sleep(20)
                                else:
                                    logger.warning(f"⚠️ Beklenmeyen HTTP kodu: {head_response.status_code}")
                                    break
                                    
                            except Exception as e:
                                logger.warning(f"⚠️ URL kontrol hatası: {str(e)[:100]}")
                                time.sleep(20)
                    
                    if not downloaded:
                        logger.warning(f"⚠️ Bu key ile video indirilemedi: {api_key[:8]}...")
                            
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON parse hatası: {str(e)}")
                    logger.debug(f"📄 Raw response: {data[:500]}")
                    
            elif status_code == 403:
                logger.warning(f"⚠️ API'ye abone değilsiniz veya key geçersiz")
            elif status_code == 429:
                logger.warning(f"⚠️ Rate limit aşıldı")
            else:
                logger.warning(f"⚠️ HTTP {status_code}")
                
            # Key'ler arasında bekle
            if i < len(rapidapi_keys) - 1:
                logger.info("⏳ Sonraki key için 5 saniye bekleniyor...")
                time.sleep(5)
                
        except Exception as e:
            logger.error(f"❌ RapidAPI hatası: {str(e)}", exc_info=True)
            continue
    
    logger.error("❌ Tüm RapidAPI denemeleri başarısız!")
    return False

def download_via_pytube(youtube_url, output_file):
    """Pytube ile YouTube videosu indir"""
    try:
        logger.info(f"🐍 Pytube ile indirme deneniyor: {youtube_url}")
        
        # Pytube'i dynamic import et
        from pytube import YouTube
        
        # YouTube nesnesi oluştur
        yt = YouTube(youtube_url)
        logger.info(f"📺 Video başlığı: {yt.title}")
        
        # En yüksek kaliteli stream'i bul
        stream = yt.streams.filter(
            progressive=True, 
            file_extension='mp4'
        ).order_by('resolution').desc().first()
        
        if stream:
            logger.info(f"📦 Stream bulundu: {stream.resolution}")
            logger.info(f"📥 İndirme başlatılıyor...")
            
            # Videoyu indir
            stream.download(filename=output_file)
            
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                if file_size > 1024000:
                    logger.info(f"✅ Pytube ile indirildi! ({file_size/1024/1024:.1f} MB)")
                    return True
                else:
                    logger.warning(f"⚠️ Pytube dosya çok küçük: {file_size} bytes")
                    os.remove(output_file)
        
        logger.error("❌ Pytube ile uygun stream bulunamadı")
        return False
        
    except Exception as e:
        logger.error(f"❌ Pytube hatası: {str(e)}", exc_info=True)
        return False

def get_all_rapidapi_keys():
    """Tüm RapidAPI key'lerini topla"""
    keys = []
    
    # RAPIDAPI_KEY_1, RAPIDAPI_KEY_2, ... şeklinde ara
    i = 1
    while True:
        key_name = f"RAPIDAPI_KEY_{i}"
        key_value = os.environ.get(key_name)
        
        if key_value:
            key_value = key_value.strip()
            if key_value and key_value not in keys:
                keys.append(key_value)
                logger.info(f"🔑 {key_name} bulundu: {key_value[:8]}...")
            i += 1
        else:
            if i == 1:
                logger.warning(f"⚠️ RAPIDAPI_KEY_1 bulunamadı")
            break
    
    # Eski formatı da kontrol et
    old_keys = os.environ.get("RAPIDAPI_KEYS", "")
    if old_keys:
        for key in old_keys.split(','):
            key = key.strip()
            if key and key not in keys:
                keys.append(key)
                logger.info(f"🔑 Eski format RapidAPI Key bulundu: {key[:8]}...")
    
    logger.info(f"📊 Toplam {len(keys)} RapidAPI anahtarı bulundu")
    return keys

# ============================================
# 3. YARDIMCI FONKSİYONLAR
# ============================================
def extract_video_id(url):
    """YouTube URL'den video ID çıkar"""
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
    
    logger.warning(f"⚠️ Video ID çıkarılamadı: {url}")
    return url.split('/')[-1]

def get_youtube_url_from_tmdb(tmdb_id, api_key):
    """TMDB'den YouTube URL'sini al"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
        params = {'api_key': api_key, 'language': 'tr-TR'}
        logger.info(f"📡 TMDB Videos API çağrısı: {url}")
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        logger.info(f"📊 TMDB Videos: {len(data.get('results', []))} video bulundu")
        
        # Fragmanları önceliklendir
        for video in data.get('results', []):
            if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
                video_url = f"https://www.youtube.com/watch?v={video['key']}"
                logger.info(f"✅ TMDB'den fragman bulundu: {video['name']}")
                return video_url
        
        # Diğer YouTube videoları
        for video in data.get('results', []):
            if video.get('site') == 'YouTube':
                video_url = f"https://www.youtube.com/watch?v={video['key']}"
                logger.info(f"✅ TMDB'den video bulundu: {video['name']}")
                return video_url
                
    except Exception as e:
        logger.error(f"❌ TMDB video çekme hatası: {str(e)}", exc_info=True)
    
    logger.warning("⚠️ TMDB'den YouTube videosu bulunamadı")
    return None

# ============================================
# 4. 3 KATMANLI İÇERİK SİSTEMİ
# ============================================
def get_main_content_via_3layer(youtube_url, tmdb_id, film_adi, duration, output_file):
    """3 katmanla ana içerik videosunu al."""
    
    youtube_id = extract_video_id(youtube_url) if youtube_url else None
    logger.info(f"🎯 Video ID: {youtube_id}")
    
    # KATMAN 1: Gelişmiş yt-dlp
    logger.info("="*60)
    logger.info("KATMAN 1: Gelişmiş yt-dlp")
    logger.info("="*60)
    
    if youtube_url:
        if download_ytdlp_enhanced(youtube_url, output_file):
            return True
    else:
        logger.warning("⚠️ YouTube URL yok, Katman 1 atlanıyor")
    
    # KATMAN 2: RapidAPI (Yeni endpoint)
    logger.info("="*60)
    logger.info("KATMAN 2: RapidAPI (Yeni Endpoint)")
    logger.info("="*60)
    
    if youtube_id:
        if download_via_rapidapi_direct(youtube_id, output_file):
            return True
    else:
        logger.warning("⚠️ YouTube ID yok, Katman 2 atlanıyor")
    
    # KATMAN 3: Pytube
    logger.info("="*60)
    logger.info("KATMAN 3: Pytube")
    logger.info("="*60)
    
    if youtube_url:
        if download_via_pytube(youtube_url, output_file):
            return True
    else:
        logger.warning("⚠️ YouTube URL yok, Katman 3 atlanıyor")
    
    # KATMAN 4: TMDB Sinematik İçerik (fallback)
    logger.info("="*60)
    logger.info("KATMAN 4: TMDB Sinematik İçerik")
    logger.info("="*60)
    
    return create_cinematic_content(tmdb_id, film_adi, duration, output_file)

def create_cinematic_content(tmdb_id, film_adi, duration, output_file):
    """TMDB'den sinematik içerik oluştur."""
    try:
        TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
        if not TMDB_KEY:
            logger.error("❌ TMDB_API_KEY yok")
            return False
        
        logger.info(f"🎬 TMDB Sinematik içerik oluşturuluyor: {film_adi}")
        
        # TMDB'den backdrop al
        tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
        params = {'api_key': TMDB_KEY, 'language': 'tr-TR'}
        response = requests.get(tmdb_url, params=params, timeout=15)
        film_data = response.json()
        
        backdrop_path = film_data.get('backdrop_path')
        if not backdrop_path and film_data.get('images', {}).get('backdrops'):
            backdrop_path = film_data['images']['backdrops'][0]['file_path']
        
        if backdrop_path:
            backdrop_url = f"https://image.tmdb.org/t/p/original{backdrop_path}"
            backdrop_file = f"backdrop_content_{tmdb_id}.jpg"
            
            logger.info(f"📥 Backdrop indiriliyor: {backdrop_url}")
            with open(backdrop_file, 'wb') as f:
                f.write(requests.get(backdrop_url).content)
            
            # Font
            font_path = "assets/font.ttf"
            if not os.path.exists(font_path):
                font_path = "Arial"
            
            # Sinematik içerik oluştur
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1', '-i', backdrop_file,
                '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                '-vf', f"scale=1920:1080,"
                       f"zoompan=z='min(zoom+0.0005,1.2)':d={int(duration*25)}:s=1920x1080,"
                       f"drawtext=text='{film_adi}':fontfile='{font_path}':"
                       f"fontcolor=white:fontsize=36:"
                       f"box=1:boxcolor=black@0.5:x=(w-text_w)/2:y=h-100",
                '-c:v', 'libx264', '-preset', 'fast', '-t', str(duration),
                '-c:a', 'aac', '-b:a', '128k',
                output_file
            ]
            
            logger.info(f"🎬 FFmpeg sinematik içerik oluşturuyor")
            subprocess.run(cmd, check=True, timeout=300)
            os.remove(backdrop_file)
            
            logger.info(f"✅ Sinematik içerik oluşturuldu: {output_file}")
            return True
        else:
            logger.error("⚠️ TMDB'de backdrop bulunamadı")
            
    except Exception as e:
        logger.error(f"❌ Sinematik içerik hatası: {e}", exc_info=True)
    
    return False

# ============================================
# 5. BİRLEŞTİRME ve TTS
# ============================================
def combine_cover_and_content(cover_path, content_path, output_path):
    """Kapak ve içeriği birleştir."""
    try:
        if not os.path.exists(cover_path):
            logger.error(f"❌ Kapak dosyası bulunamadı: {cover_path}")
            return False
        if not os.path.exists(content_path):
            logger.error(f"❌ İçerik dosyası bulunamadı: {content_path}")
            return False
        
        logger.info("🔗 Videolar birleştiriliyor...")
        
        # Önce dosya sürelerini kontrol et
        try:
            cmd_cover = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1', cover_path]
            cmd_content = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                          '-of', 'default=noprint_wrappers=1:nokey=1', content_path]
            
            cover_duration = float(subprocess.run(cmd_cover, capture_output=True, text=True).stdout.strip())
            content_duration = float(subprocess.run(cmd_content, capture_output=True, text=True).stdout.strip())
            
            logger.info(f"⏱️ Kapak süresi: {cover_duration:.2f}s")
            logger.info(f"⏱️ İçerik süresi: {content_duration:.2f}s")
        except:
            logger.warning("⚠️ Süreler alınamadı, varsayılan değerler kullanılıyor")
        
        # Basit birleştirme
        cmd = [
            'ffmpeg', '-y',
            '-i', cover_path,
            '-i', content_path,
            '-filter_complex', 
            '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]',
            '-map', '[outv]',
            '-map', '[outa]',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart',
            output_path
        ]
        
        logger.debug(f"🔧 FFmpeg birleştirme komutu: {' '.join(cmd[:5])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"✅ Birleştirme tamamlandı: {output_path} ({file_size/1024/1024:.1f} MB)")
                return True
            else:
                logger.error("❌ Birleştirilmiş dosya oluşmadı")
        else:
            logger.error(f"❌ FFmpeg birleştirme hatası: {result.stderr[:500]}")
            
    except Exception as e:
        logger.error(f"❌ Birleştirme hatası: {e}", exc_info=True)
    
    return False

def get_tts_duration(tts_url):
    """TTS sesinin süresini al."""
    try:
        logger.info(f"🔊 TTS süresi alınıyor: {tts_url}")
        
        # TTS'yi indir
        tts_temp = "temp_tts.mp3"
        response = requests.get(tts_url, timeout=30)
        with open(tts_temp, 'wb') as f:
            f.write(response.content)
        
        # Süreyi al
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
    
    return 180  # Varsayılan

def add_tts_to_video(video_path, tts_url, output_path):
    """TTS sesini videoya ekle."""
    try:
        logger.info(f"🔊 TTS ekleniyor: {tts_url}")
        
        # TTS'yi indir
        tts_file = "tts_temp.mp3"
        response = requests.get(tts_url, timeout=30)
        tts_size = len(response.content)
        
        with open(tts_file, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"📦 TTS boyutu: {tts_size/1024:.1f} KB")
        
        if tts_size < 1024:
            logger.error("⚠️ TTS dosyası çok küçük")
            os.remove(tts_file)
            return False
        
        # Videoya TTS'yi ekle
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
        
        logger.info(f"🎬 FFmpeg TTS ekliyor")
        subprocess.run(cmd, check=True, timeout=300)
        os.remove(tts_file)
        
        logger.info(f"✅ TTS eklendi: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ TTS ekleme hatası: {e}", exc_info=True)
        if os.path.exists("tts_temp.mp3"):
            os.remove("tts_temp.mp3")
        return False

# ============================================
# 6. ANA İŞ AKIŞI
# ============================================
def main():
    logger.info("="*60)
    logger.info("🚀 1+3+1 OTOMATİK SİSTEM BAŞLATILIYOR")
    logger.info("="*60)
    
    try:
        # GitHub event verilerini al
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path or not os.path.exists(event_path):
            logger.warning("❌ GITHUB_EVENT_PATH bulunamadı! Test modu...")
            p = {
                "film_id": "test_001",
                "tmdb_id": "1233413",
                "film_adi": "Günahkârlar",
                "ses_url": "https://prodopsy.com/youtube/audio/ses_3.mp3",
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
        logger.info(f"🔊 TTS URL: {ses_url}")
        logger.info(f"📡 Callback: {callback}")
        
        # ADIM 1: SİNEMATİK KAPAK
        logger.info("\n" + "="*60)
        logger.info("ADIM 1: SİNEMATİK KAPAK OLUŞTURMA")
        logger.info("="*60)
        
        cover_file = create_unified_cover(tmdb_id, film_adi)
        if not cover_file:
            logger.error("❌ Kapak oluşturulamadı, işlem iptal.")
            return False
        
        # ADIM 2: 3 KATMANLA İÇERİK
        logger.info("\n" + "="*60)
        logger.info("ADIM 2: 3 KATMANLA ANA İÇERİK")
        logger.info("="*60)
        
        TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
        youtube_url = None
        
        if TMDB_KEY:
            youtube_url = get_youtube_url_from_tmdb(tmdb_id, TMDB_KEY)
            if youtube_url:
                logger.info(f"🔗 YouTube URL: {youtube_url}")
            else:
                logger.warning("⚠️ TMDB'den YouTube URL'si alınamadı")
        else:
            logger.warning("⚠️ TMDB_API_KEY yok, YouTube URL alınamıyor")
        
        tts_duration = get_tts_duration(ses_url)
        
        content_file = f"content_{film_id}.mp4"
        if not get_main_content_via_3layer(youtube_url, tmdb_id, film_adi, tts_duration, content_file):
            logger.error("❌ İçerik alınamadı! İşlem sonlandırılıyor.")
            return False
        
        # ADIM 3: BİRLEŞTİRME ve TTS
        logger.info("\n" + "="*60)
        logger.info("ADIM 3: BİRLEŞTİRME ve TTS")
        logger.info("="*60)
        
        combined_file = f"combined_{film_id}.mp4"
        if not combine_cover_and_content(cover_file, content_file, combined_file):
            logger.warning("⚠️ Birleştirme başarısız, sadece içerik kullanılacak.")
            combined_file = content_file
        
        final_file = f"final_{film_id}.mp4"
        if not add_tts_to_video(combined_file, ses_url, final_file):
            logger.warning("⚠️ TTS eklenemedi, sessiz video gönderilecek.")
            final_file = combined_file
        
        # ADIM 4: CALLBACK
        logger.info("\n" + "="*60)
        logger.info("ADIM 4: CALLBACK GÖNDERİMİ")
        logger.info("="*60)
        
        try:
            if os.path.exists(final_file):
                file_size = os.path.getsize(final_file) / (1024*1024)
                logger.info(f"📦 Video boyutu: {file_size:.1f} MB")
                
                with open(final_file, 'rb') as f:
                    files = {'video': (f'fragman_{film_id}.mp4', f, 'video/mp4')}
                    data = {'film_id': film_id, 'status': 'success'}
                    response = requests.post(callback, files=files, data=data, timeout=180)
                    
                    logger.info(f"📡 Callback durumu: {response.status_code}")
                    if response.status_code != 200:
                        logger.error(f"❌ Callback hatası: {response.text[:200]}")
                    else:
                        logger.info("✅ Callback başarılı!")
            else:
                logger.error("❌ Final video dosyası bulunamadı!")
                
        except Exception as e:
            logger.error(f"❌ Callback hatası: {e}", exc_info=True)
        
        # TEMİZLİK
        logger.info("\n🧹 Temizlik yapılıyor...")
        temp_files = [cover_file, content_file, combined_file, final_file]
        
        for temp_file in temp_files:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.debug(f"✅ Silindi: {temp_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Silinemedi {temp_file}: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ 1+3+1 SİSTEMİ BAŞARIYLA TAMAMLANDI!")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ana iş akışı hatası: {e}", exc_info=True)
        return False

# ============================================
# ÇALIŞTIR
# ============================================
if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.error("⏹️ Kullanıcı tarafından durduruldu")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Beklenmeyen hata: {e}", exc_info=True)
        sys.exit(1)
