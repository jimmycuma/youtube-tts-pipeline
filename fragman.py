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

import logging
import sys
from datetime import datetime

def setup_logging():
    logger = logging.getLogger("fragman_logger")
    logger.setLevel(logging.DEBUG)

    # Aynı handler tekrar eklenmesin
    if logger.handlers:
        return logger

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)

    # File handler (utf-8)
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
        languages = ["tr-TR", "tr", "en-US", "en", None]

        for lang in languages:
            url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
            params = {'api_key': api_key}

            if lang:
                params["language"] = lang

            response = requests.get(url, params=params, timeout=15)

            if response.status_code != 200:
                logger.error(f"❌ TMDB videos API hata ({lang}): {response.status_code}")
                continue

            data = response.json()
            results = data.get("results", [])

            if not results:
                logger.warning(f"⚠️ TMDB sonuç yok ({lang})")
                continue

            # Önce Trailer ara
            for video in results:
                if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                    key = video.get("key")
                    name = video.get("name", "")
                    logger.info(f"✅ TMDB Trailer bulundu ({lang}): {name}")
                    return f"https://www.youtube.com/watch?v={key}"

            # Trailer yoksa herhangi YouTube video al
            for video in results:
                if video.get("site") == "YouTube":
                    key = video.get("key")
                    name = video.get("name", "")
                    logger.info(f"✅ TMDB YouTube video bulundu ({lang}): {name}")
                    return f"https://www.youtube.com/watch?v={key}"

        logger.warning("⚠️ TMDB içinde hiçbir dilde YouTube fragman bulunamadı")
        return None

    except Exception as e:
        logger.error(f"❌ TMDB fragman bulma hatası: {str(e)}")
        return None


# ============================================
# RAPIDAPI İLE İNDİRME
# ============================================

def download_via_rapidapi(youtube_id, output_file):
    rapidapi_keys = get_rapidapi_keys()
    if not rapidapi_keys:
        logger.error("❌ RapidAPI key yok")
        return False

    api_host = "youtube-video-fast-downloader-24-7.p.rapidapi.com"
    api_url = f"https://{api_host}/get-video-info/{youtube_id}"

    for api_key in rapidapi_keys:
        try:
            logger.info(f"🚀 RapidAPI deneniyor: {api_key[:8]}...")

            headers = {
                "x-rapidapi-key": api_key.strip(),
                "x-rapidapi-host": api_host
            }

            r = requests.get(api_url, headers=headers, timeout=60)

            if r.status_code != 200:
                logger.warning(f"⚠️ RapidAPI HTTP {r.status_code}: {r.text[:200]}")
                time.sleep(2)
                continue

            data = r.json()

            # mp4 linkini bul
            video_url = None

            # bazı apiler direkt linki "url" veya "download_url" verir
            if "url" in data:
                video_url = data["url"]

            if not video_url and "download_url" in data:
                video_url = data["download_url"]

            # bazıları "formats" listesi verir
            if not video_url and "formats" in data:
                formats = data["formats"]
                # en düşük kaliteyi seç (daha hızlı)
                for f in formats:
                    if f.get("ext") == "mp4" and f.get("url"):
                        video_url = f["url"]
                        break

            # bazıları "links" verir
            if not video_url and "links" in data:
                links = data["links"]
                for f in links:
                    if f.get("url") and "mp4" in f.get("url"):
                        video_url = f["url"]
                        break

            if not video_url:
                logger.warning("⚠️ MP4 link bulunamadı")
                continue

            logger.info(f"📥 MP4 indiriliyor: {video_url[:80]}...")

            with requests.get(video_url, stream=True, timeout=300) as download:
                download.raise_for_status()
                with open(output_file, "wb") as f:
                    for chunk in download.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000000:
                logger.info(f"✅ Video indirildi: {os.path.getsize(output_file)/1024/1024:.1f} MB")
                return True
            else:
                logger.warning("⚠️ Dosya bozuk veya küçük geldi")
                if os.path.exists(output_file):
                    os.remove(output_file)

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
