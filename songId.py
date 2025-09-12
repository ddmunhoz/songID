import os
import asyncio
from shazamio import Shazam, Serialize
from typing import List, Dict
from mutagen import File
from mutagen.id3 import ID3, TIT2, TPE1, TALB


def update_tags_and_rename(file_path, artist, title, cover_url, album=None):
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
    """
    Recognizes tracks in a given folder using the Shazam API.

    Args:
        folder_path (str): The path to the folder containing audio files.

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary
                    contains the file path and recognition result.
    """
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
                out = await shazam.recognize(file_path)
                if out and out.get('track'):
                    track = out['track']
                    title = track.get('title')
                    artist = track.get('subtitle')
                    album = track.get('albumadamid', None)
                    release_date = track.get('releasedate', None)
                    
                    url = track.get('url')
                    cover_url = track.get('images', {}).get('coverart', None)

                    print(f"✅  Found: Title: '{title}', Artist: '{artist}'")
                    print(f"    Release Date: {release_date}")
                    print(f"    Cover Art: {cover_url}")
               
                    update_tags_and_rename(file_path, artist, title, cover_url, album)
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