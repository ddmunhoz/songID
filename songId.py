import os
import sys
import asyncio
from shazamio import Shazam, Serialize
from typing import List, Dict
from mutagen import File
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error, COMM, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover
import requests
import pydantic
import shutil
import json
import time
import math
import logging
from pprint import pformat
from logging.handlers import TimedRotatingFileHandler
from appdirs import user_config_dir
from pathlib import Path

from tools.messaging_signal import signalBot
from tools.appConfig import appConfig

class songIdentificator:
    SCRIPT_DIR = Path(__file__).parent
    CONFIG_DIR = Path(user_config_dir("config"))

    def __init__(self):
        self.logger = self._setup_logging("INFO")
        self.config = {}
        self.notify_bot_signal = None
        self._reload_config()  # Initial config load

    def _setup_logging(self,lvl) -> logging.Logger:
        """Sets up a timed rotating file logger."""
        log_path = self.SCRIPT_DIR / "logs" / "log.txt"
        log_path.parent.mkdir(exist_ok=True)
        logger = logging.getLogger("log")
      
        handler = TimedRotatingFileHandler(log_path, when="D", interval=1, backupCount=7)
        logger.setLevel(lvl)
        formatter_logs = logging.Formatter(
            fmt="%(asctime)s %(levelname)-6s %(message)s",
            datefmt="%m-%d-%y %H:%M:%S",
        )
        handler.setFormatter(formatter_logs)
        logger.addHandler(handler)

         # Console handler writing logs to console (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(lvl)  # Console shows INFO and above
        formatter_console = logging.Formatter(
            fmt="%(asctime)s %(message)s",
            datefmt="%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter_console)
        logger.addHandler(console_handler)

        self.logger_raw = logger
        return logger
    
    def _reload_config(self):
        """Loads and reloads configuration from the JSON file."""
        config_path = self.SCRIPT_DIR / "config" / "config.json"
        try:
            with open(config_path) as f:
                #config = json.load(f)
                parsedConfig = appConfig.appConfig.load_and_validate(config_path)
                #parsedConfig = appConfig.appConfig(**config)
                self.config = parsedConfig.get_data()
                
                # Update logger level dynamically
                log_level = self.config.get("logLevel").upper()
                self.logger_raw.setLevel(log_level)
                
                #self.logger_raw.setLevel(log_level)
                for handler in self.logger_raw.handlers:
                    if isinstance(handler, logging.StreamHandler):
                        handler.setLevel(log_level)

                # Update instance attributes from config
                self.check_interval = int(self.config.get("checkInterval"))
                self.max_queue_size = int(self.config.get("maxQueueSize"))
                self.rename_and_move_only = self.config.get("renameAndMoveOnly")
                signal_notifier = self.config.get("notifySignal")
                if signal_notifier:
                    self.notify_bot_signal = signalBot.signalBot(
                        self.config["signalSender"],
                        self.config["signalGroup"],
                        self.config["signalEndpoint"],
                    )
                    self.notifyEachSong = self.config.get("notifyEachSong")
                    self.notifySummary = self.config.get("notifySummary")
                else:
                    self.notify_bot_signal = None
            return
        
        except (FileNotFoundError, json.JSONDecodeError, pydantic.ValidationError, ValueError) as e:
            if isinstance(e, pydantic.ValidationError):
                errors = []
                for error in e.errors():
                    errors.append(error['msg'])
                    self.logger.critical(f"⚙️ Config validation error: {error['msg']}\n")
            else:
                self.logger.critical(f"📋 Config error: {str(e)}")
            sys.exit(1)
    
        raise RuntimeError("Failed to load config.")

    def _estimate_processing_time(self, total_files: int) -> str:
        cycles = math.ceil(total_files / self.max_queue_size)
        total_seconds = cycles * self.check_interval
        hours = total_seconds / 3600
        return hours

    def add_cover_art(self, file_path: str, cover_url: str):
        response = requests.get(cover_url)
        if response.status_code != 200:
            self.logger.error(f"Failed to download cover art from {cover_url}")
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
            self._add_cover_mp3(file_path, image_data, mime_type)
        elif ext == '.flac':
            self._add_cover_flac(file_path, image_data, mime_type)
        elif ext == '.m4a':
            self._add_cover_m4a(file_path, image_data)
        else:
            self.logger.error(f"Cover art embedding not supported for {file_path}")

    def update_mp3_tags(self, file_path: str, cover_url: str=None, add_comment: str=None):
        if add_comment:
            id3 = ID3(file_path)
            id3.add(COMM(encoding=3, lang='eng', desc='Comment', text=add_comment))
            id3.save(file_path)

        # Add cover art if present
        if cover_url:
            self.add_cover_art(file_path, cover_url)

        return id3

    def update_flac_tags(self, file_path: str, cover_url: str=None, add_comment: str=None):
        if add_comment:
            audio_flac = FLAC(file_path)
            audio_flac['comment'] = add_comment
            audio_flac.save()

        # Add cover art if present
        if cover_url:
            self.add_cover_art(file_path, cover_url)

    def update_m4a_tags(self, file_path: str, artist: str=None, title: str=None, cover_url: str=None, album: str=None, release_date: str=None, add_comment: str=None):
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

        audio.save()

        # Add cover art if present
        if cover_url:
            self.add_cover_art(file_path, cover_url)
            
        return audio

    def update_tags(self, file_path: str, artist: str=None, title: str=None, cover_url: str=None, album: str=None, release_date: str=None, add_comment: str=None):
        audio = File(file_path, easy=True)
        if audio is None:
            self.logger.critical(f"Unsupported or invalid audio file: {file_path}")
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

        if file_path.lower().endswith('.mp3'):
            self.update_mp3_tags(file_path, cover_url, add_comment=add_comment)

        elif file_path.lower().endswith('.flac'):
            self.update_flac_tags(file_path, cover_url, add_comment=add_comment)

        elif file_path.lower().endswith('.m4a'):
            self.update_m4a_tags(file_path, artist, title, cover_url, album, release_date, add_comment=add_comment)


        return file_path

    def handle_fallback(self, file_path: str, folder_path: str) -> int:
        manual_input_dir = os.path.join(folder_path, 'manual_input')
        os.makedirs(manual_input_dir, exist_ok=True)

        self.logger.debug(f"🟡Could not find {os.path.basename(file_path)}")
        self.logger.debug(f"🟡🔵Fallback using minimal tags...")
        
        if self.rename_and_move_only:
            self.logger.info(f"✅ Moving only {file_path}")
            tags = self._read_tags(file_path)
            new_path = self._rename_and_move(file_path, tags.get('artist'), tags.get('title'))
            return 3

        if self._minimal_tags_present(file_path):
            self.logger.info(f"🟡☑️ Minimal in place...processing...")
            tags = self._strip_tags(file_path)
            new_path = self._rename_and_move(file_path, tags.get('artist'), tags.get('title'))
            self.update_tags(new_path, add_comment='roybatty')
            self.logger.info(f"🟡✅Processed!")
            return 0
        else:
            self.logger.info(f"☔️ I guess all these tags are lost in time like tears in rain...")
            destination = os.path.join(manual_input_dir, os.path.basename(file_path))
            shutil.move(file_path, destination)
            self.logger.info(f"🕊️ Moved for manual input.")
            return 1

    async def recognize_tracks_in_folder(self, folder_path: str) -> List[Dict]:
        self.logger.info(f"🗄️Scanning folder: {folder_path}")
        if not os.path.isdir(folder_path):
            self.logger.error(f"Error: The folder '{folder_path}' does not exist.")
            return []

        shazam = Shazam()
        supported_extensions = ('.mp3', '.wav', '.flac', '.m4a', '.ogg')

        supported_files = [
            filename for filename in os.listdir(folder_path)
            if filename.lower().endswith(supported_extensions)
        ]

        total = len(supported_files)
        count = 0
        count_fallback = 0
        count_fallback_manual = 0
        count_skipped = 0

        for filename in supported_files:
            file_path = os.path.join(folder_path, filename)

            if self.rename_and_move_only:
                self.handle_fallback(file_path, folder_path)
                count_skipped += 1
                count += 1
                self.logger.debug(f"☑️ Rename and Move only {filename}")
                continue

            #Check comment tag before calling Shazam
            if self._has_roybatty_comment(file_path):
                count_skipped += 1
                self.logger.debug(f"☑️ Skipping {filename}")
                continue
            
            if count >= self.max_queue_size:
                self.logger.info(f"Max queue {self.max_queue_size} reached!")
                break

            self.logger.info(f"Searching... {filename}...")
            try:
                count += 1
                out = await shazam.recognize_song(file_path)
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

                    self.logger.info(f"👀Found! {artist} - {title} /{album}/{release_date}")
                    self._strip_tags(file_path)
                    new_path = self._rename_and_move(file_path, artist, title)
                    self.update_tags(new_path, artist, title, cover_url, album, release_date, add_comment='roybatty')
                    self.logger.info(f"✅Processed!")
                    if self.notify_bot_signal and self.notifyEachSong:
                        payload = {
                            "📻": f"{title} - {artist}",
                            "image_url": cover_url
                        }
                        self.logger.debug(f"✉️ sending notification {payload}")
                        self.notify_bot_signal.sendMessage(payload=payload)
                else:
                    count_fallback += 1
                    count_fallback_manual = count_fallback_manual + self.handle_fallback(file_path, folder_path)

            except Exception as e:
                self.handle_fallback(file_path, folder_path)
            
        queueProcessingDuration = self._estimate_processing_time(total)

        self.logger.info(f"🏁Processed: {count}/{total}/{count_skipped}/{count_fallback}/{count_fallback_manual} (processed/total/skip/fallback/manual)")
        self.logger.info(f"Time left: {queueProcessingDuration}")

        if self.notify_bot_signal and ((count) >= self.notifySummary):
            payload = {
                "📟": "Song IDentificator9000",
                "path": str(folder_path)[-21:],
                "processed": count,
                "total": total,
                "skipped": count_skipped,
                "fallback": count_fallback,
                "manual": count_fallback_manual
            }

            if queueProcessingDuration > 0.20:
                payload["time_left"] = f"{queueProcessingDuration:.2f}hours ⏱️"
            else:
                payload["✅"] = "completed!"
            self.logger.debug(f"✉️ sending notification {payload}")
            self.notify_bot_signal.sendMessage(payload=payload)

        return True

    def run(self):
        while True:
            start_time = time.time()
            self.logger.info("--- Starting new song identification check cycle ---")
            self._reload_config()  # Check for config changes at the start of each loop
            
            monitored_paths = self.config.get('monitored_paths')
            try:
                for path in monitored_paths:
                    asyncio.run(self.recognize_tracks_in_folder(path))
               
            except (json.JSONDecodeError) as e:
                self.logger.critical(f"Could not load monitored paths {e}")
                raise RuntimeError("Could not load monitored paths!")


            self.logger.info("--- Cycle finished ---")
            # Sleep for the remainder of the interval
            elapsed_time = time.time() - start_time
            sleep_duration = max(0, self.check_interval - elapsed_time)
            self.logger.info(f"Sleeping for {sleep_duration:.2f} seconds.")
            time.sleep(sleep_duration)

    # --- Static Helper Methods ---
    @staticmethod
    def _minimal_tags_present(file_path: str) -> bool:
        audio = File(file_path, easy=True)
        if audio is None:
            return False
        title = audio.get('title')
        artist = audio.get('artist')
        return bool(title and artist)
    
    @staticmethod
    def _has_roybatty_comment(file_path: str) -> bool:
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
            try:
                id3 = ID3(file_path)
            except ID3NoHeaderError:
                id3 = ID3()            # Create empty ID3 tag object
                id3.save(file_path) 
            
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

    @staticmethod
    def _add_cover_mp3(file_path: str, image_data: str, mime_type: str):
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
        return audio

    @staticmethod
    def _add_cover_flac(file_path: str, image_data: str, mime_type: str):
        audio = FLAC(file_path)
        image = Picture()
        image.data = image_data
        image.type = 3  # cover(front)
        image.mime = mime_type
        image.desc = "Cover"
        audio.clear_pictures()  # remove existing pictures if needed
        audio.add_picture(image)
        audio.save()
        return audio

    @staticmethod
    def _add_cover_m4a(file_path: str, image_data: str):
        audio = MP4(file_path)
        cover = MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)
        audio["covr"] = [cover]
        return audio

    @staticmethod
    def _rename_and_move(file_path: str, artist: str, title: str) -> str:
        # Sanitize artist and title for filesystem
        safe_artist = artist.replace("/", "_") if artist else "Unknown"
        safe_title = title.replace("/", "_") if title else "Unknown"

        extension = os.path.splitext(file_path)[1]
        new_name = f"{safe_artist} - {safe_title}{extension}"

        # move to artist subfolder
        parent_dir = os.path.dirname(file_path)
        target_artist_dir = os.path.join(parent_dir, safe_artist)
        os.makedirs(target_artist_dir, exist_ok=True)

        new_path = os.path.join(target_artist_dir, new_name)

        if file_path != new_path:
            os.rename(file_path, new_path)

        return new_path

    @staticmethod
    def _strip_tags(file_path: str) -> Dict[str, str]:
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
 
    @staticmethod
    def _read_tags(file_path: str) -> Dict[str, str]:
        audio = File(file_path)
        if audio is None:
            print(f"Unsupported or invalid audio file: {file_path}")
            return {}

        tags = {}
        
        easy_audio = File(file_path, easy=True)
        tags['title'] = easy_audio.get('title', [None])[0] if easy_audio else None
        tags['artist'] = easy_audio.get('artist', [None])[0] if easy_audio else None

        return tags


if __name__ == "__main__":
    songIdentificator9000 = songIdentificator()
    try:
        songIdentificator9000.run()
    except KeyboardInterrupt:
        print("\nExiting application.")
        sys.exit(0)
    except Exception:
        songIdentificator9000.logger.exception("A fatal, unhandled error occurred in the main loop.")
        sys.exit(1)
