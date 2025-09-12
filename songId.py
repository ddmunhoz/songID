import os
import asyncio
from shazamio import Shazam, Serialize
from typing import List, Dict
from mutagen import File
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error, COMM
import requests
import shutil

def handle_fallback(file_path, manual_input_dir):
    print(f"🟡Could not recognize '{os.path.basename(file_path)}'!")
    print(f"🟡🔵Trying fallback using minimal tags...")
    if minimal_tags_present(file_path):
        print(f"🟡☑️ Minimal in place...processing...")
        tags = strip_tags(file_path, keep_minimal=True)
        rename_file(file_path, tags.get('artist'), tags.get('title'))
        update_tags(file_path, artist=None, title=None, cover_url=None, add_comment='roybatty')
        print(f"🟡✅Processed and RoyBatty compliant!\n")
    else:
        print(f"☔️ I guess all these tags are lost in time like tears in rain...")
        destination = os.path.join(manual_input_dir, os.path.basename(file_path))
        shutil.move(file_path, destination)
        print(f"🕊️ Moved for manual input.\n")


def minimal_tags_present(file_path):
    audio = File(file_path, easy=True)
    if audio is None:
        return False
    title = audio.get('title')
    artist = audio.get('artist')
    return bool(title and artist)

def strip_tags(file_path, keep_minimal=False):
    audio = File(file_path)
    if audio is None:
        print(f"Unsupported or invalid audio file: {file_path}")
        return {}

    tags = {}
    if keep_minimal:
        # Save minimal tags first
        easy_audio = File(file_path, easy=True)
        tags['title'] = easy_audio.get('title', [None])[0] if easy_audio else None
        tags['artist'] = easy_audio.get('artist', [None])[0] if easy_audio else None
        tags['album'] = easy_audio.get('album', [None])[0] if easy_audio else None
        tags['date'] = easy_audio.get('date', [None])[0] if easy_audio else None

    ext = file_path.lower().split('.')[-1]
    if ext == 'mp3':
        id3 = ID3(file_path)
        if keep_minimal:
            frames_to_keep = {'TIT2', 'TPE1', 'TALB', 'TDRC', 'TYER', 'APIC'}
            for key in list(id3.keys()):
                if key not in frames_to_keep:
                    id3.delall(key)
            id3.save(file_path)
        else:
            id3.delete()
            id3.save(file_path)
    elif ext == 'flac':
        if keep_minimal:
            pictures = audio.pictures
            audio.delete()
            audio.save()
            audio = FLAC(file_path)
            if tags['title']:
                audio['TITLE'] = tags['title']
            if tags['artist']:
                audio['ARTIST'] = tags['artist']
            if tags['album']:
                audio['ALBUM'] = tags['album']
            if tags['date']:
                audio['DATE'] = tags['date']
            audio.clear_pictures()
            for pic in pictures:
                audio.add_picture(pic)
            audio.save()
        else:
            audio.delete()
            audio.clear_pictures()
            audio.save()
    else:
        audio.delete()
        audio.save()
        if keep_minimal and audio is not None:
            if tags['title']:
                audio['title'] = tags['title']
            if tags['artist']:
                audio['artist'] = tags['artist']
            if tags['album']:
                audio['album'] = tags['album']
            if tags['date']:
                audio['date'] = tags['date']
            audio.save()

    return tags

def has_roybatty_comment(file_path):
    audio = File(file_path, easy=True)
    if audio is None:
        return False

    # Check easy tag 'comment'
    comments = audio.get('comment', [])
    if 'roybatty' in (c.lower() for c in comments):
        return True
    # For MP3, additionally check raw ID3
    if file_path.lower().endswith('.mp3'):
        id3 = ID3(file_path)
        for comm in id3.getall("COMM"):
            if 'roybatty' in comm.text[0].lower():
                return True
    return False

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

def add_cover_art(file_path, cover_url):
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

def rename_file(file_path, artist, title):
    safe_artist = artist.replace("/", "_") if artist else "Unknown"
    safe_title = title.replace("/", "_") if title else "Unknown"

    directory = os.path.dirname(file_path)
    extension = os.path.splitext(file_path)[1]
    new_name = f"{safe_artist} - {safe_title}{extension}"
    new_path = os.path.join(directory, new_name)
    
    if file_path != new_path:
        os.rename(file_path, new_path)
        print(f"     Renamed to: {new_path}")
    else:
        print("     Filename already correct.")
    
    return new_path

def update_tags(file_path, artist=None, title=None, cover_url=None, album=None, release_date=None, add_comment=None):
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

    audio.save()

    if add_comment:
        if file_path.lower().endswith('.mp3'):
            from mutagen.id3 import ID3, COMM
            id3 = ID3(file_path)
            id3.add(COMM(encoding=3, lang='eng', desc='Comment', text=add_comment))
            id3.save(file_path)
        elif file_path.lower().endswith('.flac'):
            from mutagen.flac import FLAC
            audio_flac = FLAC(file_path)
            audio_flac['comment'] = add_comment
            audio_flac.save()

    if cover_url:
        add_cover_art(file_path, cover_url)

    return file_path



async def recognize_tracks_in_folder(folder_path: str) -> List[Dict]:
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return []

    shazam = Shazam()
    recognized_results = []
    supported_extensions = ('.mp3', '.wav', '.flac', '.m4a', '.ogg')

    manual_input_dir = os.path.join(folder_path, 'manual_input')
    os.makedirs(manual_input_dir, exist_ok=True)


    print(f"🗄️Scanning folder: {folder_path}\n")

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(supported_extensions):
            file_path = os.path.join(folder_path, filename)
            
            # Check comment tag before calling Shazam
            if has_roybatty_comment(file_path):
                print(f"☑️ Skipping '{filename}!' RoyBatty has it covered!")
                recognized_results.append({
                    'file_path': file_path,
                    'title': None,
                    'artist': None,
                    'album': None,
                    'release_date': None,
                    'url': None,
                    'cover_url': None,
                    'skipped': True
                })
                continue

            print(f"\n⏰Recognizing '{filename}'...")
            try:
                out = await shazam.recognize(file_path)  # updated method usage
                if out and out.get('track'):
                    track = out['track']
                    album = None
                    release_date = None
                    for section in track.get('sections', []):
                        if section.get('type') == 'SONG' and 'metadata' in section:
                            album = section['metadata'][0].get('text') if section['metadata'] else None
                            release_date =  section['metadata'][2].get('text') if section['metadata'] else None
                            break

                    title = track.get('title')
                    artist = track.get('subtitle')
                    url = track.get('url')
                    cover_url = track.get('images', {}).get('coverart', None)

                    print(f"\n✅  Found: Title: '{title}', Artist: '{artist}'")
                    print(f"    Album: {album}")
                    print(f"    Release Date: {release_date}")
                    print(f"    Cover Art: {cover_url}")
                   
                    update_tags(file_path, artist, title, cover_url, album, release_date, add_comment='roybatty')
                    rename_file(file_path, artist, title)
                    recognized_results.append({
                        'file_path': file_path,
                        'title': title,
                        'artist': artist,
                        'album': album,
                        'release_date': release_date,
                        'url': url,
                        'cover_url': cover_url,
                        'skipped': False
                    })

                else:
                   handle_fallback(file_path, manual_input_dir)

            except Exception as e:
                handle_fallback(file_path, manual_input_dir)

    return recognized_results


async def main():
    folder_to_scan = '/Users/munhoz/Desktop/Projects/Code/active/mine/songId/songs' 
    results = await recognize_tracks_in_folder(folder_to_scan)
    

if __name__ == "__main__":
    asyncio.run(main())