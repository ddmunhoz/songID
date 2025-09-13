# songID

**songID** is an automated music identification and tagging tool for audio files. It scans specified folders for new songs, uses Shazam to recognize tracks, and updates their metadata (artist, title, album, cover art, etc.). Optionally, it can send notifications via Signal when new tracks are processed.

## Features

- Automatically scans folders for new audio files.
- Identifies songs using Shazam.
- Updates audio file tags (artist, title, album, release date, comments).
- Embeds cover art into files.
- Skips already processed files (using a comment tag).
- Handles fallback/manual tagging for unrecognized tracks.
- Sends notifications via Signal (with cover art) when enabled.
- Rotating log file and console logging.
- Configurable scan interval and queue size to avoid excessive requests.
- Summary notifications after batch processing.
- Manual input folder for files needing human tagging.

## Supported Formats

- MP3
- FLAC
- M4A
- WAV
- OGG

## Configuration

All settings are managed via a JSON config file located at `config/config.json` in the project folder.

**Example:**

```json
{
    "monitored_paths": [
        "/path/to/your/music/folder",
        "/another/path/to/scan"
    ],
    "notifySignal": true,
    "notifyEachSong": false,
    "notifySummary": 5,
    "checkInterval": 15,
    "maxQueueSize": 20,
    "logLevel": "INFO",
    "signalSender": "+1234567890",
    "signalGroup": "group.YourSignalGroupID==",
    "signalEndpoint": "http://your.signal.server:port"
}