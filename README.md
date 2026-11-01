# YouTube Channel ID Extractor

A command-line tool that extracts the YouTube channel ID and RSS feed URL from any YouTube URL. Paste in a video link, channel handle, or any other YouTube URL format and get back the underlying channel ID and its corresponding RSS feed.

## Supported URL Formats

- `youtube.com/@username` — handle
- `youtube.com/channel/CHANNEL_ID` — direct channel ID
- `youtube.com/c/channelname` — custom URL
- `youtube.com/user/username` — legacy username
- `youtube.com/watch?v=VIDEO_ID` — video page (wrap in quotes)
- `youtu.be/VIDEO_ID` — short link

URLs with or without `https://`, `www.`, and trailing slashes all work.

## Prerequisites

- **Python 3.6+** — uses only the standard library (no third-party packages to install)
- **YouTube Data API v3 key** — get one free at https://console.cloud.google.com/apis/credentials (enable the "YouTube Data API v3" for your project)

## Setup

1. Clone the repository:

   ```
   git clone <repo-url>
   cd youtube-channel-id-extractor
   ```

2. Provide your API key using one of these methods:

   - **`.env` file (recommended):** create a `.env` file in the project root with:
     ```
     YOUTUBE_API_KEY=your_key_here
     ```

   - **Environment variable:**
     ```
     export YOUTUBE_API_KEY=your_key_here
     ```
   - **CLI flag:** pass `--api-key` on each run (see below)

## Usage

```
python extract.py <youtube-url>
```

Examples:

```
python extract.py "https://www.youtube.com/@mkbhd"
python extract.py "https://youtu.be/dQw4w9WgXcQ"
python extract.py --api-key YOUR_KEY "youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw"
```

Output:

```
Channel ID:   UCXuqSBlHAE6Xw-yeJA0Tunw
RSS Feed URL: https://www.youtube.com/feeds/videos.xml?channel_id=UCXuqSBlHAE6Xw-yeJA0Tunw
```

## Running Tests

Tests use **pytest** — the only dependency beyond the standard library.

```
pip install pytest
pytest
```
