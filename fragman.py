#!/usr/bin/env python3
"""
fragman.py - 1+3+1 Otomatik Film İnceleme Sistemi
1. Sinematik Kapak → 2. 3 Katmanlı İçerik → 3. Birleştirme
"""

import os, json, requests, subprocess, time, sys, tempfile, random

# ============================================
# 1. SİNEMATİK KAPAK OLUŞTURMA
# ============================================
def create_unified_cover(tmdb_id, film_adi, cover_duration=5):
    """TMDB görselleriyle sinematik kapak oluştur."""
    
    print(f"🎨 Sinematik kapak oluşturuluyor: {film_adi}")
    
    TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
    if not TMDB_KEY:
        print("⚠️ TMDB_API_KEY bulunamadı. Basit kapak kullanılacak.")
        return create_simple_cover(film_adi, f"cover_{tmdb_id}.mp4")
    
    temp_files = []
    cover_file = f"cover_{tmdb_id}.mp4"
    
    try:
        # TMDB'den film detaylarını al
        tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
        params = {'api_key': TMDB_KEY, 'language': 'tr-TR', 'append_to_response': 'images'}
        response = requests.get(tmdb_url, params=params, timeout=15)
        film_data = response.json()
        
        # Görselleri seç
        backdrop_path = film_data.get('backdrop_path')
        poster_path = film_data.get('poster_path')
        
        if not backdrop_path and film_data.get('images', {}).get('backdrops'):
            backdrop_path = film_data['images']['backdrops'][0]['file_path']
        if not poster_path and film_data.get('images', {}).get('posters'):
            poster_path = film_data['images']['posters'][0]['file_path']
        
        # Görselleri indir
        base_url = "https://image.tmdb.org/t/p/original"
        
        backdrop_file = None
        poster_file = None
        
        if backdrop_path:
            backdrop_url = f"{base_url}{backdrop_path}"
            backdrop_file = f"backdrop_{tmdb_id}.jpg"
            with open(backdrop_file, 'wb') as f:
                f.write(requests.get(backdrop_url, timeout=20).content)
            temp_files.append(backdrop_file)
        
        if poster_path:
            poster_url = f"{base_url}{poster_path}"
            poster_file = f"poster_{tmdb_id}.jpg"
            with open(poster_file, 'wb') as f:
                f.write(requests.get(poster_url, timeout=20).content)
            temp_files.append(poster_file)
        
        # Film bilgileri
        year = film_data.get('release_date', '')[:4] if film_data.get('release_date') else ''
        title_display = f"{film_adi} ({year})" if year else film_adi
        
        # FFmpeg komutu - SİNEMATİK KAPAK
        # Font yolunu kontrol et
        font_path = "assets/font.ttf"
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if not os.path.exists(font_path):
                # Sistemde herhangi bir font bul
                cmd = ['fc-match', '-f', '%{file}']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    font_path = result.stdout.strip()
                else:
                    font_path = "Arial"  # Varsayılan font adı
        
        filter_parts = []
        
        # Backdrop işleme
        if backdrop_file:
            filter_parts.append(
                f"movie={backdrop_file},scale=1920:1080,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
                f"colorchannelmixer=aa=0.6,"  # %40 karartma
                f"zoompan=z='1.00':d={cover_duration*25}[bg]"
            )
        else:
            filter_parts.append(f"color=c=black:s=1920x1080:d={cover_duration}[bg]")
        
        # Poster ekleme (sağ tarafta)
        if poster_file:
            filter_parts.append(
                f"movie={poster_file},scale=400:-1[poster];"
                f"[bg][poster]overlay=x=W-w-80:y=(H-h)/2[bg_with_poster]"
            )
            bg_layer = "bg_with_poster"
        else:
            bg_layer = "bg"
        
        # Film adı (büyük, ortada)
        filter_parts.append(
            f"[{bg_layer}]drawtext=fontfile='{font_path}':"
            f"text='{title_display}':fontcolor=white:fontsize=86:"
            f"borderw=4:bordercolor=black@0.8:"
            f"x=(w-text_w)/2:y=(h-text_h)/2-50:"
            f"alpha='if(lt(t,1),0,if(lt(t,2),(t-1)/1,1))'[with_title]"
        )
        
        # "İNCELEME" yazısı (turkuaz)
        filter_parts.append(
            f"[with_title]drawtext=fontfile='{font_path}':"
            f"text='İ N C E L E M E':fontcolor=#40E0D0:fontsize=42:"
            f"borderw=2:bordercolor=black@0.6:"
            f"x=(w-text_w)/2:y=(h-text_h)/2+60[with_subtitle];"
            # Altına çizgi
            f"[with_subtitle]drawbox=x=(w-180)/2:y=(h-text_h)/2+110:"
            f"w=180:h=3:color=#40E0D0:t=fill[final]"
        )
        
        # Grain efekti (sinematik his)
        filter_parts.append(
            f"[final]noise=c0s=8:allf=t[grainy];"
            f"[grainy]fade=t=in:st=0:d=1,fade=t=out:st={cover_duration-1}:d=1[output]"
        )
        
        filter_complex = ";".join(filter_parts)
        
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
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(cover_file):
            print(f"✅ Kapak oluşturuldu: {cover_file}")
            return cover_file
        else:
            print(f"❌ FFmpeg hatası: {result.stderr[:200]}")
            
    except Exception as e:
        print(f"❌ Kapak hatası: {str(e)[:200]}")
    
    finally:
        # Temizlik
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
    
    # Fallback: Basit kapak
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
        subprocess.run(cmd, check=True, timeout=30)
        print(f"✅ Basit kapak oluşturuldu: {output_file}")
        return output_file
    except Exception as e:
        print(f"❌ Basit kapak hatası: {e}")
        return None

def download_ytdlp_enhanced(youtube_url, output_file, max_attempts=3):
    """Gelişmiş yt-dlp ile YouTube videosu indir"""
    
    for attempt in range(max_attempts):
        try:
            print(f"🔄 YT-DLP Deneme {attempt+1}/{max_attempts}")
            
            # Rastgele user-agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            ]
            
            cmd = [
                'yt-dlp',
                '--no-cookies',
                '--geo-bypass',
                '--retries', '5',
                '--fragment-retries', '5',
                '--socket-timeout', '30',
                '--user-agent', random.choice(user_agents),
                '-f', 'best[height<=720]/best[height<=480]/best',
                '-o', output_file,
                '--quiet',
                youtube_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    if file_size > 102400:  # 100KB'den büyük
                        print(f"✅ yt-dlp ile indirildi! ({file_size/1024/1024:.1f} MB)")
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

def download_via_rapidapi_with_key_rotation(youtube_id, output_file, api_keys_str):
    """RapidAPI anahtar döngüsü ile indir"""
    if not api_keys_str or not youtube_id:
        return False
    
    api_keys = [key.strip() for key in api_keys_str.split(',') if key.strip()]
    if not api_keys:
        return False
    
    print(f"🔑 {len(api_keys)} RapidAPI anahtarı mevcut")
    
    # Anahtarları karıştır (load balancing)
    random.shuffle(api_keys)
    
    for i, api_key in enumerate(api_keys):
        try:
            print(f"  RapidAPI anahtar {i+1}/{len(api_keys)} deneniyor...")
            
            # Örnek RapidAPI endpoint - gerçek endpoint'i kullanın
            url = "https://youtube-video-download-info.p.rapidapi.com/dl"
            querystring = {"id": youtube_id}
            headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "youtube-video-download-info.p.rapidapi.com"
            }
            
            response = requests.get(url, headers=headers, params=querystring, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Video URL'sini bul
                if 'link' in data and data['link']:
                    video_url = data['link'][0] if isinstance(data['link'], list) else data['link']
                    
                    # Videoyu indir
                    video_response = requests.get(video_url, stream=True, timeout=60)
                    with open(output_file, 'wb') as f:
                        for chunk in video_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    if os.path.getsize(output_file) > 102400:
                        print(f"✅ RapidAPI ile indirildi!")
                        return True
                
        except Exception as e:
            print(f"❌ RapidAPI hatası: {str(e)[:100]}")
            continue
    
    return False

def extract_video_id(url):
    """YouTube URL'den video ID çıkar"""
    if not url: 
        return None
    
    import re
    
    # YouTube URL desenleri
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
    """TMDB'den YouTube URL'sini al"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
        params = {'api_key': api_key, 'language': 'tr-TR'}
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        for video in data.get('results', []):
            if video.get('site') == 'YouTube' and video.get('type') in ['Trailer', 'Teaser', 'Clip']:
                print(f"✅ TMDB'den YouTube videosu bulundu: {video['name']}")
                return f"https://www.youtube.com/watch?v={video['key']}"
        
        # Herhangi bir YouTube videosu
        for video in data.get('results', []):
            if video.get('site') == 'YouTube':
                print(f"✅ TMDB'den YouTube videosu bulundu: {video['name']}")
                return f"https://www.youtube.com/watch?v={video['key']}"
                
    except Exception as e:
        print(f"⚠️ TMDB video çekme hatası: {str(e)[:100]}")
    
    return None

# ============================================
# 2. 3 KATMANLI İÇERİK SİSTEMİ
# ============================================
def get_main_content_via_3layer(youtube_url, tmdb_id, film_adi, duration, output_file):
    """3 katmanla ana içerik videosunu al."""
    
    youtube_id = extract_video_id(youtube_url) if youtube_url else None
    
    # KATMAN 1: Gelişmiş yt-dlp
    print("  1. Katman: yt-dlp deneniyor...")
    if youtube_url and download_ytdlp_enhanced(youtube_url, output_file):
        return True
    
    # KATMAN 2: RapidAPI
    print("  2. Katman: RapidAPI deneniyor...")
    rapidapi_keys = os.environ.get("RAPIDAPI_KEYS", "")
    if rapidapi_keys and youtube_id:
        if download_via_rapidapi_with_key_rotation(youtube_id, output_file, rapidapi_keys):
            return True
    
    # KATMAN 3: TMDB Sinematik İçerik
    print("  3. Katman: TMDB Sinematik içerik oluşturuluyor...")
    return create_cinematic_content(tmdb_id, film_adi, duration, output_file)

def create_cinematic_content(tmdb_id, film_adi, duration, output_file):
    """TMDB'den sinematik içerik oluştur (kapsız)."""
    try:
        TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
        if not TMDB_KEY:
            print("⚠️ TMDB_API_KEY yok, sinematik içerik oluşturulamıyor")
            return False
        
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
            with open(backdrop_file, 'wb') as f:
                f.write(requests.get(backdrop_url).content)
            
            # Font yolunu kontrol et
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
            
            subprocess.run(cmd, check=True, timeout=300)
            os.remove(backdrop_file)
            print(f"✅ Sinematik içerik oluşturuldu: {output_file}")
            return True
        else:
            print("⚠️ TMDB'de backdrop bulunamadı")
            
    except Exception as e:
        print(f"❌ Sinematik içerik hatası: {e}")
    
    return False

# ============================================
# 3. BİRLEŞTİRME ve TTS
# ============================================
def combine_cover_and_content(cover_path, content_path, output_path):
    """Kapak ve içeriği birleştir."""
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', cover_path,
            '-i', content_path,
            '-filter_complex', '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]',
            '-map', '[outv]', '-map', '[outa]',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            output_path
        ]
        subprocess.run(cmd, check=True, timeout=300)
        print(f"✅ Birleştirme tamamlandı: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Birleştirme hatası: {e}")
        return False

def add_tts_to_video(video_path, tts_url, output_path):
    """TTS sesini videoya ekle."""
    try:
        # TTS'yi indir
        tts_file = "tts_temp.mp3"
        print(f"🔊 TTS indiriliyor: {tts_url}")
        response = requests.get(tts_url, timeout=30)
        with open(tts_file, 'wb') as f:
            f.write(response.content)
        
        # TTS süresini kontrol et
        tts_size = os.path.getsize(tts_file)
        if tts_size < 1024:  # 1KB'den küçükse hata
            print("⚠️ TTS dosyası çok küçük")
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
        subprocess.run(cmd, check=True, timeout=300)
        os.remove(tts_file)
        print(f"✅ TTS eklendi: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ TTS ekleme hatası: {e}")
        # Temizlik
        if os.path.exists("tts_temp.mp3"):
            os.remove("tts_temp.mp3")
        return False

def get_tts_duration(tts_url):
    """TTS sesinin süresini al."""
    try:
        # TTS indir ve süreyi ölç
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
            print(f"⏱️ TTS süresi: {duration:.1f} saniye")
            return duration
            
    except Exception as e:
        print(f"⚠️ TTS süresi alınamadı: {e}")
    
    return 180  # Varsayılan süre: 3 dakika

# ============================================
# 4. ANA İŞ AKIŞI (1+3+1 MODEL)
# ============================================
def main():
    try:
        # GitHub event verilerini al
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path or not os.path.exists(event_path):
            print("❌ GITHUB_EVENT_PATH bulunamadı!")
            # Manuel test için
            p = {
                "film_id": "test_001",
                "tmdb_id": "551",  # The Mummy
                "film_adi": "Anakonda",
                "ses_url": "https://api.streamelements.com/kappa/v2/speech?voice=Filiz&text=Merhaba bu bir test",
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
        
        print(f"🎬 Film: {film_adi}")
        print(f"🚀 1+3+1 Otomatik Sistem Başlatılıyor...\n")
        
        # ADIM 1: SİNEMATİK KAPAK
        print("="*60)
        print("ADIM 1: SİNEMATİK KAPAK OLUŞTURMA")
        print("="*60)
        
        cover_file = create_unified_cover(tmdb_id, film_adi)
        if not cover_file:
            print("❌ Kapak oluşturulamadı, işlem iptal.")
            return False
        
        # ADIM 2: 3 KATMANLA İÇERİK
        print("\n" + "="*60)
        print("ADIM 2: 3 KATMANLA ANA İÇERİK")
        print("="*60)
        
        # YouTube URL'sini al
        TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
        youtube_url = None
        if TMDB_KEY:
            youtube_url = get_youtube_url_from_tmdb(tmdb_id, TMDB_KEY)
            if youtube_url:
                print(f"🔗 YouTube URL: {youtube_url}")
            else:
                print("⚠️ TMDB'den YouTube URL'si alınamadı")
        
        # TTS süresini al
        tts_duration = get_tts_duration(ses_url)
        
        # 3 Katmanla içerik al
        content_file = f"content_{film_id}.mp4"
        if not get_main_content_via_3layer(youtube_url, tmdb_id, film_adi, tts_duration, content_file):
            print("❌ İçerik alınamadı!")
            # Yedek: Siyah ekran
            return create_fallback_video(film_adi, tts_duration, content_file)
        
        # ADIM 3: BİRLEŞTİRME ve TTS
        print("\n" + "="*60)
        print("ADIM 3: BİRLEŞTİRME ve TTS")
        print("="*60)
        
        combined_file = f"combined_{film_id}.mp4"
        if not combine_cover_and_content(cover_file, content_file, combined_file):
            print("⚠️ Birleştirme başarısız, sadece içerik kullanılacak.")
            combined_file = content_file
        
        final_file = f"final_{film_id}.mp4"
        if not add_tts_to_video(combined_file, ses_url, final_file):
            print("⚠️ TTS eklenemedi, sessiz video gönderilecek.")
            final_file = combined_file
        
        # ADIM 4: CALLBACK
        print("\n" + "="*60)
        print("ADIM 4: CALLBACK GÖNDERİMİ")
        print("="*60)
        
        try:
            if os.path.exists(final_file):
                file_size = os.path.getsize(final_file) / (1024*1024)
                print(f"📦 Video boyutu: {file_size:.1f} MB")
                
                with open(final_file, 'rb') as f:
                    files = {'video': (f'fragman_{film_id}.mp4', f, 'video/mp4')}
                    data = {'film_id': film_id, 'status': 'success'}
                    response = requests.post(callback, files=files, data=data, timeout=180)
                    print(f"📡 Callback durumu: {response.status_code}")
                    if response.status_code != 200:
                        print(f"⚠️ Callback hatası: {response.text[:200]}")
            else:
                print("❌ Final video dosyası bulunamadı!")
                
        except Exception as e:
            print(f"❌ Callback hatası: {e}")
        
        # TEMİZLİK
        print("\n🧹 Temizlik yapılıyor...")
        for temp_file in [cover_file, content_file, combined_file, final_file]:
            if temp_file and os.path.exists(temp_file) and temp_file != final_file:
                try:
                    os.remove(temp_file)
                except:
                    pass
        
        print("\n✅ 1+3+1 SİSTEMİ TAMAMLANDI!")
        return True
        
    except Exception as e:
        print(f"❌ Ana iş akışı hatası: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_fallback_video(film_adi, duration, output_file):
    """Yedek video oluştur (siyah ekran + yazı)."""
    try:
        font_path = "assets/font.ttf"
        if not os.path.exists(font_path):
            font_path = "Arial"
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s=1920x1080:d={duration}',
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-vf', f"drawtext=text='{film_adi}':fontfile='{font_path}':"
                   f"fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2,"
                   f"drawtext=text='İçerik hazırlanıyor...':fontfile='{font_path}':"
                   f"fontcolor=yellow:fontsize=36:x=(w-text_w)/2:y=h-100",
            '-c:v', 'libx264', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '128k',
            '-t', str(duration),
            output_file
        ]
        subprocess.run(cmd, check=True, timeout=60)
        print(f"✅ Yedek video oluşturuldu: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Yedek video hatası: {e}")
        return False

# ============================================
# ÇALIŞTIR
# ============================================
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
