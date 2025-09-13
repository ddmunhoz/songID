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
```

### Config Options

- **monitored_paths**: List of folders to scan for new songs.
- **notifySignal**: Set to `true` to enable Signal notifications.
- **notifyEachSong**: If `true`, sends a notification for each processed song.
- **notifySummary**: Minimum number of processed songs before sending a summary notification.
- **checkInterval**: Time (in seconds) between scan cycles.
- **maxQueueSize**: Maximum number of files processed per scan cycle (prevents excessive requests).
- **logLevel**: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- **signalSender**: Your Signal sender phone number (format: `+1234567890`).
- **signalGroup**: Signal group ID (format: `group.xxxxx==`).
- **signalEndpoint**: URL of your Signal REST API server.

## Usage

1. **Install dependencies** (see requirements.txt or use pip for Python packages).
2. **Edit `config/config.json`** with your paths and Signal settings.
3. **Run the script**:

    ```sh
    python songId.py
    ```

The tool will continuously scan your folders, process new songs, and log its activity.

## Logging

Logs are saved in `logs/log.txt` and rotated daily. Console output is also provided.

## Request Limits & Best Practices

**Important:**  
Shazam and Signal APIs may rate-limit or block you if you make too many requests in a short period.
- Use `maxQueueSize` and `checkInterval` to control how many files are processed per cycle and how often scans occur.
- Avoid setting these values too high, especially if scanning large folders or running frequently.
- Respect API terms of service and avoid unnecessary repeated scans.

## Troubleshooting

- Make sure your config file is valid JSON and all required fields are present.
- Ensure your Signal REST API server is running and accessible if notifications are enabled.
- Supported audio formats must have readable tags.

## License

MIT License