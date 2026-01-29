#!/usr/bin/env python3
"""
fragman.py - YouTube'dan fragman indir, TTS sesi ile birleştir
"""

import os
import sys
import json
import requests
import yt_dlp
import subprocess
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip

# GitHub event verilerini al
def get_github_data():
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if event_path:
        with open(event_path, 'r') as f:
            return json.load(f)
    return None

def get_tmdb_trailer(tmdb_id, api_key):
    """TMDB'den fragman URL'sini al"""
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
    params = {
        'api_key': api_key,
        'language': 'tr-TR'
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # Önce trailer bul
        for video in data.get('results', []):
            if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                return f"https://www.youtube.com/watch?v={video['key']}"
        
        # Trailer yoksa herhangi bir YouTube videosu
        for video in data.get('results', []):
            if video.get('site') == 'YouTube':
                return f"https://www.youtube.com/watch?v={video['key']}"
                
    except Exception as e:
        print(f"❌ TMDB hatası: {e}")
    
    return None

def download_youtube_video(url, output_path='trailer.mp4'):
    """YouTube'dan video indir"""
    ydl_opts = {
        'format': 'best[height<=720]/best',  # 720p veya daha iyi
        'outtmpl': output_path,
        'quiet': False,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"✅ İndirildi: {info['title']}")
            return True
    except Exception as e:
        print(f"❌ YouTube indirme hatası: {e}")
        return False

def mix_audio_video(video_path, tts_path, output_path='final.mp4'):
    """Video ve TTS sesini birleştir"""
    try:
        # Video'yu yükle
        video = VideoFileClip(video_path)
        
        # TTS sesini yükle
        tts_audio = AudioFileClip(tts_path)
        
        # Orijinal sesi %20 seviyesine düşür
        original_audio = video.audio.volumex(0.2)
        
        # TTS sesinin süresini videoya uydur
        # Eğer TTS daha kısa ise, videoyu kısalt
        if tts_audio.duration < video.duration:
            video = video.subclip(0, tts_audio.duration)
            original_audio = video.audio.volumex(0.2) if video.audio else None
        
        # Sesleri birleştir
        if original_audio:
            final_audio = CompositeAudioClip([original_audio, tts_audio])
        else:
            final_audio = tts_audio
        
        # Yeni videoyu oluştur
        final_video = video.set_audio(final_audio)
        
        # Yaz (hızlı encode için preset)
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            preset='fast'  # ultrafast, superfast, veryfast, faster, fast, medium
        )
        
        # Belleği temizle
        video.close()
        tts_audio.close()
        final_video.close()
        
        print(f"✅ Video işlendi: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Video işleme hatası: {e}")
        return False

def main():
    # 1. GitHub event verilerini al
    event_data = get_github_data()
    if not event_data:
        print("❌ GitHub event verisi alınamadı")
        sys.exit(1)
    
    client_payload = event_data['client_payload']
    film_id = client_payload['film_id']
    tmdb_id = client_payload['tmdb_id']
    film_adi = client_payload['film_adi']
    ses_url = client_payload['ses_url']
    callback_url = client_payload['callback']
    
    print(f"🎬 Film: {film_adi} (ID: {film_id})")
    
    # 2. TMDB API Key
    tmdb_api_key = os.environ.get('TMDB_API_KEY')
    if not tmdb_api_key:
        print("❌ TMDB_API_KEY bulunamadı")
        sys.exit(1)
    
    # 3. TMDB'den fragman URL'sini al
    print("🔍 TMDB'den fragman aranıyor...")
    youtube_url = get_tmdb_trailer(tmdb_id, tmdb_api_key)
    
    if not youtube_url:
        print("❌ YouTube fragmanı bulunamadı")
        sys.exit(1)
    
    print(f"📹 YouTube URL: {youtube_url}")
    
    # 4. YouTube'dan fragmanı indir
    trailer_path = f"trailer_{film_id}.mp4"
    if not download_youtube_video(youtube_url, trailer_path):
        sys.exit(1)
    
    # 5. TTS sesini indir
    tts_path = f"tts_{film_id}.mp3"
    try:
        response = requests.get(ses_url)
        with open(tts_path, 'wb') as f:
            f.write(response.content)
        print(f"🔊 TTS indirildi: {tts_path}")
    except Exception as e:
        print(f"❌ TTS indirme hatası: {e}")
        sys.exit(1)
    
    # 6. Video ve sesi birleştir
    output_path = f"final_{film_id}.mp4"
    if not mix_audio_video(trailer_path, tts_path, output_path):
        sys.exit(1)
    
    # 7. Callback'e gönder
    try:
        with open(output_path, 'rb') as video_file:
            files = {'video': (output_path, video_file, 'video/mp4')}
            data = {'film_id': film_id}
            
            print(f"📤 Callback'e gönderiliyor: {callback_url}")
            response = requests.post(callback_url, files=files, data=data)
            
            if response.status_code == 200:
                print("✅ Callback başarılı")
            else:
                print(f"❌ Callback hatası: {response.status_code}")
                print(response.text)
                
    except Exception as e:
        print(f"❌ Callback gönderme hatası: {e}")
    
    # 8. Geçici dosyaları temizle
    for temp_file in [trailer_path, tts_path, output_path]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"🧹 Temizlendi: {temp_file}")

if __name__ == "__main__":
    main()
