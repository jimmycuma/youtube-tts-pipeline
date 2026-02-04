#!/usr/bin/env python3
"""
fragman.py - Film İnceleme Fragman Sistemi (SADECE RAPIDAPI)
- TMDB'den fragman YouTube ID alır
- RapidAPI ile indirir (3 key fallback)
- Ses dosyasının süresine göre videoyu kırpar
- Ses ile videoyu birleştirir
- Callback ile sunucuya gönderir
"""

import os
import json
import time
import sys
import logging
import requests
import subprocess
import http.client
from datetime import datetime

# ============================================
# LOGLAMA
# ============================================

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)

    log_filename = f"fragman_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
 file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()

# ============================================
# RAPIDAPI KEY SİSTEMİ
# ============================================

def get_rapidapi_keys():
    keys = []

    # RAPIDAPI_KEY_1,2,3 şeklinde
    for i in range(1, 6):
        key_name = f"RAPIDAPI_KEY_{i}"
        key_value = os.environ.get(key_name)
        if key_value:
            key_value = key_value.strip()
            if key_value and key_value not in keys:
                keys.append(key_value)
                logger.info(f"🔑 {key_name} bulundu: {key_value[:8]}...")

    # RAPIDAPI_KEYS env varsa onu da destekle
    old_keys = os.environ.get("RAPIDAPI_KEYS", "")
    if old_keys:
        for key in old_keys.split(','):
            key = key.strip()
            if key and key not in keys:
                keys.append(key)
                logger.info(f"🔑 RAPIDAPI_KEYS içinden key alındı: {key[:8]}...")

    logger.info(f"📊 Toplam RapidAPI key sayısı: {len(keys)}")
    return keys


# ============================================
# YOUTUBE ID ÇIKARMA
# ============================================

def extract_video_id(url):
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

    # son çare
    return url.split('/')[-1]


# ============================================
# TMDB'DEN FRAGMAN BUL
# ============================================

def get_youtube_url_from_tmdb(tmdb_id, api_key):
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
        params = {'api_key': api_key, 'language': 'tr-TR'}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            logger.error(f"❌ TMDB videos API hata: {response.status_code}")
            return None

        data = response.json()
        results = data.get("results", [])

        # Önce Trailer ara
        for video in results:
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                key = video.get("key")
                name = video.get("name", "")
                logger.info(f"✅ TMDB Trailer bulundu: {name}")
                return f"https://www.youtube.com/watch?v={key}"

        # Trailer yoksa herhangi YouTube video
        for video in results:
            if video.get("site") == "YouTube":
                key = video.get("key")
                name = video.get("name", "")
                logger.info(f"✅ TMDB YouTube video bulundu: {name}")
                return f"https://www.youtube.com/watch?v={key}"

        logger.warning("⚠️ TMDB içinde YouTube fragman bulunamadı")
        return None

    except Exception as e:
        logger.error(f"❌ TMDB fragman bulma hatası: {str(e)}")
        return None


# ============================================
# RAPIDAPI İLE İNDİRME
# ============================================

def download_via_rapidapi_fast(youtube_id, output_file):
    rapidapi_keys = get_rapidapi_keys()
    if not rapidapi_keys:
        logger.error("❌ RapidAPI key yok")
        return False

    api_endpoint = "youtube-video-fast-downloader-24-7.p.rapidapi.com"
    api_path = f"/download_video/{youtube_id}?quality=247"

    for api_key in rapidapi_keys:
        try:
            logger.info(f"🚀 RapidAPI deneniyor: {api_key[:8]}...")

            conn = http.client.HTTPSConnection(api_endpoint)
            headers = {
                "x-rapidapi-key": api_key,
                "x-rapidapi-host": api_endpoint
            }

            conn.request("GET", api_path, headers=headers)
            res = conn.getresponse()
            body = res.read().decode("utf-8")

            if res.status != 200:
                logger.warning(f"⚠️ RapidAPI HTTP {res.status}: {body[:200]}")
                time.sleep(2)
                continue

            try:
                video_info = json.loads(body)
            except:
                logger.warning(f"⚠️ JSON parse edilemedi: {body[:200]}")
                time.sleep(2)
                continue

            video_url = video_info.get("file")
            reserved_url = video_info.get("reserved_file", video_url)

            if not video_url:
                logger.warning("⚠️ RapidAPI file URL vermedi")
                time.sleep(2)
                continue

            logger.info(f"📌 RapidAPI URL alındı, video hazırlanıyor...")

            # Video hazır olana kadar bekle (max 300sn)
            for wait_seconds in range(0, 300, 20):
                for url in [video_url, reserved_url]:
                    try:
                        logger.info(f"⏳ Kontrol {wait_seconds}/300: {url[:60]}...")

                        head = requests.head(url, timeout=10, allow_redirects=True)
                        if head.status_code == 200:
                            size = head.headers.get("content-length")
                            if size and int(size) > 1000000:
                                logger.info(f"✅ Video hazır: {int(size)/1024/1024:.1f} MB")

                                r = requests.get(url, stream=True, timeout=180)
                                with open(output_file, "wb") as f:
                                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                                        if chunk:
                                            f.write(chunk)

                                if os.path.exists(output_file):
                                    file_size = os.path.getsize(output_file)
                                    if file_size > 1000000:
                                        logger.info(f"✅ RapidAPI ile indirildi: {file_size/1024/1024:.1f} MB")
                                        return True
                                    else:
                                        logger.warning(f"⚠️ Dosya küçük geldi: {file_size} bytes")
                                        os.remove(output_file)
                        elif head.status_code == 404:
                            logger.info("⏳ Video hazır değil (404), bekleniyor...")

                    except Exception as e:
                        logger.warning(f"⚠️ URL kontrol hatası: {str(e)[:120]}")

                time.sleep(20)

            logger.warning(f"⚠️ Bu key ile video hazırlanamadı: {api_key[:8]}...")
            time.sleep(2)

        except Exception as e:
            logger.error(f"❌ RapidAPI hata: {str(e)[:200]}")
            time.sleep(2)

    logger.error("❌ Tüm RapidAPI key'ler başarısız")
    return False


# ============================================
# SES SÜRESİ AL
# ============================================

def get_audio_duration(audio_path):
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            duration = float(result.stdout.strip())
            logger.info(f"🔊 Ses süresi: {duration:.2f} saniye")
            return duration

    except Exception as e:
        logger.error(f"❌ Ses süresi alınamadı: {e}")

    return 180.0


# ============================================
# VİDEO KIRP
# ============================================

def trim_video(video_path, duration, output_path):
    try:
        logger.info(f"✂️ Video kırpılıyor: {duration:.2f} saniye")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(output_path):
            logger.info("✅ Video kırpıldı")
            return True

        logger.error(f"❌ Video kırpma hatası: {result.stderr[:300]}")
        return False

    except Exception as e:
        logger.error(f"❌ Video kırpma exception: {e}")
        return False


# ============================================
# SES İLE BİRLEŞTİR
# ============================================

def merge_audio_video(video_path, audio_path, output_path):
    try:
        logger.info("🎧 Ses + video birleştiriliyor")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(output_path):
            logger.info("✅ Ses birleştirildi")
            return True

        logger.error(f"❌ Ses birleştirme hatası: {result.stderr[:300]}")
        return False

    except Exception as e:
        logger.error(f"❌ Ses birleştirme exception: {e}")
        return False


# ============================================
# CALLBACK UPLOAD
# ============================================

def upload_to_callback(callback_url, film_id, final_video_path):
    try:
        logger.info(f"📡 Callback gönderiliyor: {callback_url}")

        with open(final_video_path, "rb") as f:
            files = {"video": (f"fragman_{film_id}.mp4", f, "video/mp4")}
            data = {"film_id": film_id, "status": "success"}

            response = requests.post(callback_url, files=files, data=data, timeout=300)

        logger.info(f"📡 Callback status: {response.status_code}")
        logger.info(f"📡 Callback cevap: {response.text[:200]}")

        return response.status_code == 200

    except Exception as e:
        logger.error(f"❌ Callback upload hatası: {e}")
        return False


# ============================================
# MAIN
# ============================================

def main():
    logger.info("=" * 70)
    logger.info("🚀 SADECE RAPIDAPI FRAGMAN SİSTEMİ BAŞLADI")
    logger.info("=" * 70)

    try:
        event_path = os.environ.get("GITHUB_EVENT_PATH")

        if not event_path or not os.path.exists(event_path):
            logger.error("❌ GITHUB_EVENT_PATH yok. Bu sistem GitHub Actions payload ister.")
            return False

        event = json.load(open(event_path, encoding="utf-8"))
        payload = event.get("client_payload", {})

        film_id = payload.get("film_id")
        tmdb_id = payload.get("tmdb_id")
        film_adi = payload.get("film_adi")
        ses_url = payload.get("ses_url")
        callback = payload.get("callback")

        if not film_id or not tmdb_id or not film_adi or not ses_url or not callback:
            logger.error("❌ Payload eksik. film_id / tmdb_id / film_adi / ses_url / callback şart.")
            return False

        logger.info(f"🎬 Film: {film_adi}")
        logger.info(f"🎯 Film ID: {film_id}")
        logger.info(f"📌 TMDB ID: {tmdb_id}")
        logger.info(f"🔊 Ses URL: {ses_url}")

        TMDB_KEY = os.environ.get("TMDB_API_KEY", "")
        if not TMDB_KEY:
            logger.error("❌ TMDB_API_KEY yok")
            return False

        # 1) TMDB -> YouTube URL bul
        youtube_url = get_youtube_url_from_tmdb(tmdb_id, TMDB_KEY)
        if not youtube_url:
            logger.error("❌ TMDB fragman YouTube URL bulunamadı")
            return False

        logger.info(f"🔗 Fragman URL: {youtube_url}")

        # 2) YouTube ID çıkar
        youtube_id = extract_video_id(youtube_url)
        if not youtube_id:
            logger.error("❌ YouTube ID çıkarılamadı")
            return False

        logger.info(f"🆔 YouTube ID: {youtube_id}")

        # 3) Ses indir
        audio_file = f"audio_{film_id}.mp3"
        logger.info("📥 Ses indiriliyor...")

        r = requests.get(ses_url, timeout=120)
        if r.status_code != 200:
            logger.error(f"❌ Ses indirilemedi: HTTP {r.status_code}")
            return False

        with open(audio_file, "wb") as f:
            f.write(r.content)

        if not os.path.exists(audio_file) or os.path.getsize(audio_file) < 5000:
            logger.error("❌ Ses dosyası bozuk veya çok küçük")
            return False

        logger.info(f"✅ Ses indirildi: {audio_file}")

        # 4) Ses süresi
        audio_duration = get_audio_duration(audio_file)

        # 5) RapidAPI ile video indir
        raw_video = f"raw_{film_id}.mp4"
        if not download_via_rapidapi_fast(youtube_id, raw_video):
            logger.error("❌ RapidAPI video indirilemedi")
            return False

        # 6) Video kırp (ses süresi kadar)
        trimmed_video = f"trimmed_{film_id}.mp4"
        if not trim_video(raw_video, audio_duration, trimmed_video):
            logger.error("❌ Video kırpılamadı")
            return False

        # 7) Ses + video birleştir
        final_video = f"final_{film_id}.mp4"
        if not merge_audio_video(trimmed_video, audio_file, final_video):
            logger.error("❌ Video + ses birleştirilemedi")
            return False

        if not os.path.exists(final_video):
            logger.error("❌ Final video oluşmadı")
            return False

        file_size = os.path.getsize(final_video) / (1024 * 1024)
        logger.info(f"🎉 Final video hazır: {file_size:.1f} MB")

        # 8) Callback upload
        ok = upload_to_callback(callback, film_id, final_video)
        if not ok:
            logger.error("❌ Callback başarısız")
            return False

        logger.info("✅ Callback başarılı!")

        # 9) Temizlik
        logger.info("🧹 Temizlik yapılıyor...")

        for f in [audio_file, raw_video, trimmed_video, final_video]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass

        logger.info("=" * 70)
        logger.info("✅ SİSTEM TAMAMLANDI")
        logger.info("=" * 70)

        return True

    except Exception as e:
        logger.error(f"❌ MAIN HATA: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
