import os
import asyncio
from shazamio import Shazam, Serialize
from typing import List, Dict
from mutagen import File
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error, COMM
from mutagen.mp4 import MP4
import requests
import shutil

def handle_fallback(file_path, folder_path):
    manual_input_dir = os.path.join(folder_path, 'manual_input')
    os.makedirs(manual_input_dir, exist_ok=True)

    print(f"🟡Could not recognize '{os.path.basename(file_path)}'!")
    print(f"🟡🔵Trying fallback using minimal tags...")
    if minimal_tags_present(file_path):
        print(f"🟡☑️ Minimal in place...processing...")
        tags = strip_tags(file_path)
        new_path = rename_file(file_path, tags.get('artist'), tags.get('title'))
        update_tags(new_path, artist=None, title=None, cover_url=None, add_comment='roybatty')
        print(f"🟡✅Processed and RoyBatty compliant!\n")
        return 0
    else:
        print(f"☔️ I guess all these tags are lost in time like tears in rain...")
        destination = os.path.join(manual_input_dir, os.path.basename(file_path))
        shutil.move(file_path, destination)
        print(f"🕊️ Moved for manual input.\n")
        return 1

def minimal_tags_present(file_path):
    audio = File(file_path, easy=True)
    if audio is None:
        return False
    title = audio.get('title')
    artist = audio.get('artist')
    return bool(title and artist)

def strip_tags(file_path):
    audio = File(file_path)
    if audio is None:
        print(f"Unsupported or invalid audio file: {file_path}")
        return {}

    tags = {}
    
    # Save minimal tags first
    easy_audio = File(file_path, easy=True)
    tags['title'] = easy_audio.get('title', [None])[0] if easy_audio else None
    tags['artist'] = easy_audio.get('artist', [None])[0] if easy_audio else None
    tags['album'] = easy_audio.get('album', [None])[0] if easy_audio else None
    tags['date'] = easy_audio.get('date', [None])[0] if easy_audio else None

    ext = file_path.lower().split('.')[-1]
    if ext == 'mp3':
        id3 = ID3(file_path)
        # Always strip comments
        id3.delall("COMM")
        frames_to_keep = {'TIT2', 'TPE1', 'TALB', 'TDRC', 'TYER', 'APIC'}
        for key in list(id3.keys()):
            if key not in frames_to_keep:
                id3.delall(key)
        id3.save(file_path)
        
    elif ext == 'flac':
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
        audio.save()
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
    ext = os.path.splitext(file_path)[1].lower()
    audio = File(file_path, easy=True)
    if audio is None:
        return False

    # Generic easy tag 'comment' (works for FLAC, OGG, generic, sometimes M4A)
    comments = audio.get('comment', [])
    if any('roybatty' in str(c).lower() for c in comments):
        return True

    # MP3 raw ID3 check
    if ext == '.mp3':
        id3 = ID3(file_path)
        for comm in id3.getall("COMM"):
            if 'roybatty' in comm.text[0].lower():
                return True

    # FLAC direct field check
    if ext == '.flac':
        audio_flac = FLAC(file_path)
        comments = audio_flac.get('comment', [])
        if any('roybatty' in str(c).lower() for c in comments):
            return True

    # M4A/MP4 comment check
    if ext == '.m4a':
        audio_mp4 = MP4(file_path)
        # Apple uses '\xa9cmt' for comment
        comments = audio_mp4.tags.get('\xa9cmt', [])
        if any('roybatty' in str(c).lower() for c in comments):
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

def update_m4a_tags(file_path, artist=None, title=None, cover_url=None, album=None, release_date=None, add_comment=None):
    audio = MP4(file_path)
    # Apple uses special key names for tags:
    if artist:
        audio["\xa9ART"] = artist
    if title:
        audio["\xa9nam"] = title
    if album:
        audio["\xa9alb"] = album
    if release_date:
        audio["\xa9day"] = release_date
    if add_comment:
        audio["\xa9cmt"] = add_comment

    # Add cover art if present
    if cover_url:
        import requests
        response = requests.get(cover_url)
        if response.status_code == 200:
            image_data = response.content
            import mutagen.mp4
            cover = mutagen.mp4.MP4Cover(image_data, imageformat=mutagen.mp4.MP4Cover.FORMAT_JPEG)
            audio["covr"] = [cover]
    audio.save()

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
        elif file_path.lower().endswith('.m4a'):
            update_m4a_tags(file_path, artist, title, cover_url, album, release_date, add_comment='roybatty')

    if cover_url:
        add_cover_art(file_path, cover_url)

    return file_path

async def recognize_tracks_in_folder(folder_path: str) -> List[Dict]:
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return []

    shazam = Shazam()
    supported_extensions = ('.mp3', '.wav', '.flac', '.m4a', '.ogg')

    print(f"🗄️Scanning folder: {folder_path}\n")

    count = 0
    count_fallback = 0
    count_fallback_manual = 0
    for filename in os.listdir(folder_path):
        count += 1
        if filename.lower().endswith(supported_extensions):
            file_path = os.path.join(folder_path, filename)
            
            # Check comment tag before calling Shazam
            if has_roybatty_comment(file_path):
                print(f"☑️ Skipping '{filename}!' RoyBatty has it covered!")
                continue

            print(f"🔦Recognizing '{filename}'...")
            try:
                out = await shazam.recognize_song(file_path)  # updated method usage
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
                    cover_url = track.get('images', {}).get('coverart', None)

                    print(f"👀Found! Title: '{title}' - Artist: '{artist} /album/release_date")
                    strip_tags(file_path)
                    new_path = rename_file(file_path, artist, title)
                    update_tags(new_path, artist, title, cover_url, album, release_date, add_comment='roybatty')
                    print(f"✅Processed and RoyBatty compliant!\n")
                else:
                    count_fallback += 1
                    count_fallback_manual = count_fallback_manual + handle_fallback(file_path, folder_path)

            except Exception as e:
                handle_fallback(file_path, folder_path)

    print(f"\n🏁Done! Processed {count} files.")
    print(f"🏁->fallback {count_fallback}")
    print(f"🏁->manual {count_fallback_manual}")
    return True

async def main():
    folder_to_scan = '/Users/munhoz/Desktop/Projects/Code/active/mine/songId/songs' 
    results = await recognize_tracks_in_folder(folder_to_scan)
    
if __name__ == "__main__":
    asyncio.run(main())