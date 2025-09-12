import os
import asyncio
from shazamio import Shazam, Serialize
from typing import List, Dict
from mutagen import File
from mutagen.id3 import ID3, TIT2, TPE1, TALB
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
import requests

def add_cover_mp3(file_path, image_data, mime_type):
    audio = MP3(file_path, ID3=ID3)
    try:
        audio.add_tags()
    except error:
        pass

    audio.tags.add(
        APIC(
            encoding=3,        # utf-8
            mime=mime_type,    # e.g., 'image/jpeg'
            type=3,            # front cover
            desc='Cover',
            data=image_data
        )
    )
    audio.save()
    print(f"Added cover art to MP3: {file_path}")

def add_cover_flac(file_path, image_data, mime_type):
    audio = FLAC(file_path)
    image = Picture()
    image.data = image_data
    image.type = 3  # cover(front)
    image.mime = mime_type
    image.desc = "Cover"
    audio.clear_pictures()  # remove existing pictures if needed
    audio.add_picture(image)
    audio.save()
    print(f"Added cover art to FLAC: {file_path}")

def add_cover_art(file_path, cover_url):
 # Download image data from cover_url
    response = requests.get(cover_url)
    if response.status_code != 200:
        print(f"Failed to download cover art from {cover_url}")
        return
    
    image_data = response.content
    # Guess MIME from url extension (could be improved)
    ext = os.path.splitext(cover_url)[1].lower()
    if ext == '.png':
        mime_type = 'image/png'
    else:
        mime_type = 'image/jpeg'  # default fallback

    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.mp3':
        add_cover_mp3(file_path, image_data, mime_type)
    elif ext == '.flac':
        add_cover_flac(file_path, image_data, mime_type)
    else:
        print(f"Cover art embedding not supported for {file_path}")

def update_tags_and_rename(file_path, artist, title, cover_url, album=None, release_date=None):
    audio = File(file_path, easy=True)
    if audio is None:
        print(f"Unsupported or invalid audio file: {file_path}")
        return file_path
    
    if artist:
        audio["artist"] = artist
    if title:
        audio["title"] = title
    if album:
        audio["album"] = album
    if release_date:
        audio["date"] = release_date
    if cover_url:
        add_cover_art(file_path, cover_url)
    
    audio.save()
    
    # Sanitize filename
    safe_artist = artist.replace("/", "_") if artist else "Unknown"
    safe_title = title.replace("/", "_") if title else "Unknown"

    directory = os.path.dirname(file_path)
    extension = os.path.splitext(file_path)[1]
    new_name = f"{safe_artist} - {safe_title}{extension}"
    new_path = os.path.join(directory, new_name)
    
    if file_path != new_path:
        os.rename(file_path, new_path)
        print(f"Renamed to: {new_path}")
    else:
        print("Filename already correct.")
    
    return new_path


async def recognize_tracks_in_folder(folder_path: str) -> List[Dict]:
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return []

    shazam = Shazam()
    recognized_results = []
    
    # Supported file extensions based on ffmpeg/shazamio
    supported_extensions = ('.mp3', '.wav', '.flac', '.m4a', '.ogg')

    print(f"Scanning folder: {folder_path}\n")

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(supported_extensions):
            file_path = os.path.join(folder_path, filename)
            print(f"Recognizing '{filename}'...")
            try:
                out = await shazam.recognize_song(file_path)
                if out and out.get('track'):
                    track = out['track']
                    
                    for section in track.get('sections', []):
                        if section.get('type') == 'SONG' and 'metadata' in section:
                            album = section['metadata'][0].get('text') if section['metadata'] else None
                            release_date =  section['metadata'][2].get('text') if section['metadata'] else None
                            break
                    
                    title = track.get('title')
                    artist = track.get('subtitle')
                    album = album 
                    release_date = release_date
                    
                    url = track.get('url')
                    cover_url = track.get('images', {}).get('coverart', None)

                    print(f"\n✅  Found: Title: '{title}', Artist: '{artist}'")
                    print(f"    Album: {album}")
                    print(f"    Release Date: {release_date}")
                    print(f"    Cover Art: {cover_url}")
               
                    update_tags_and_rename(file_path, artist, title, cover_url, album, release_date)
                    recognized_results.append({
                        'file_path': file_path,
                        'title': title,
                        'artist': artist,
                        'album': album,
                        'release_date': release_date,
                        'url': url,
                        'cover_url': cover_url
                    })

                else:
                    print("❌  Could not recognize the track.\n")

            except Exception as e:
                print(f"❌  An error occurred while recognizing '{filename}': {e}\n")
        
    return recognized_results

async def main():
    folder_to_scan = '/Users/munhoz/Desktop/Projects/Code/active/mine/songId/songs' 
    results = await recognize_tracks_in_folder(folder_to_scan)
    

if __name__ == "__main__":
    asyncio.run(main())