#!/usr/bin/env python3
"""Extract YouTube channel ID and RSS feed URL from various YouTube URL formats."""

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

API_BASE = "https://www.googleapis.com/youtube/v3"
RSS_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={}"


def parse_youtube_url(url):
    """Parse a YouTube URL and return (url_type, identifier)."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path.rstrip("/")

    # youtu.be/VIDEO_ID
    if host in ("youtu.be", "www.youtu.be"):
        video_id = path.lstrip("/")
        if video_id:
            return ("video", video_id)

    # youtube.com variants
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
        # /watch?v=VIDEO_ID
        if path == "/watch":
            qs = parse_qs(parsed.query)
            video_id = qs.get("v", [None])[0]
            if video_id:
                return ("video", video_id)

        # /channel/UC...
        if path.startswith("/channel/"):
            channel_id = path.split("/channel/", 1)[1]
            if channel_id:
                return ("channel_id", channel_id)

        # /@username
        if path.startswith("/@"):
            handle = path[2:]
            if handle:
                return ("handle", handle)

        # /c/channelname
        if path.startswith("/c/"):
            name = path[3:]
            if name:
                return ("custom", name)

        # /user/username
        if path.startswith("/user/"):
            username = path[6:]
            if username:
                return ("user", username)

    return (None, None)


def api_get(endpoint, params, api_key):
    """Make a GET request to the YouTube Data API."""
    params["key"] = api_key
    url = f"{API_BASE}/{endpoint}?{urlencode(params)}"
    with urlopen(url) as resp:
        return json.loads(resp.read().decode())


def resolve_channel_id(url_type, identifier, api_key):
    """Resolve a channel ID from the parsed URL info."""

    if url_type == "channel_id":
        data = api_get("channels", {"part": "snippet", "id": identifier}, api_key)
        if data.get("items"):
            return identifier
        print(f"Error: Channel ID '{identifier}' not found.")
        print("Tip: Double-check the channel ID — it usually starts with 'UC'.")
        sys.exit(1)

    if url_type == "handle":
        data = api_get("channels", {"part": "snippet", "forHandle": identifier}, api_key)
        if data.get("items"):
            return data["items"][0]["id"]
        print(f"Error: No channel found for handle '@{identifier}'.")
        print("Tip: Check spelling — handles are case-sensitive.")
        sys.exit(1)

    if url_type == "user":
        data = api_get("channels", {"part": "snippet", "forUsername": identifier}, api_key)
        if data.get("items"):
            return data["items"][0]["id"]
        print(f"Error: No channel found for user '{identifier}'.")
        print("Tip: This is a legacy URL format. Try the channel's @handle URL instead.")
        sys.exit(1)

    if url_type == "custom":
        # /c/ custom URLs have no direct API parameter.
        # Try forHandle first (handles often match custom URLs), then fall back to search.
        data = api_get("channels", {"part": "snippet", "forHandle": identifier}, api_key)
        if data.get("items"):
            return data["items"][0]["id"]

        # Fallback: search (costs 100 quota units instead of 1)
        data = api_get(
            "search",
            {"part": "snippet", "q": identifier, "type": "channel", "maxResults": 1},
            api_key,
        )
        if data.get("items"):
            return data["items"][0]["snippet"]["channelId"]

        print(f"Error: No channel found for custom URL '/c/{identifier}'.")
        print("Tip: Try the channel's @handle or /channel/ID URL instead.")
        sys.exit(1)

    if url_type == "video":
        data = api_get("videos", {"part": "snippet", "id": identifier}, api_key)
        if data.get("items"):
            return data["items"][0]["snippet"]["channelId"]
        print(f"Error: Video '{identifier}' not found.")
        print("Tip: Verify the video ID is correct and the video is public.")
        sys.exit(1)

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract YouTube channel ID and RSS feed URL from a YouTube URL.",
    )
    parser.add_argument("url", help="YouTube URL to extract channel ID from")
    parser.add_argument(
        "--api-key",
        help="YouTube Data API v3 key (default: YOUTUBE_API_KEY env var)",
    )
    args = parser.parse_args()

    # Load .env file if present (replaces python-dotenv dependency)
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())

    api_key = args.api_key or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: No API key provided.")
        print()
        print("Option 1: Create a .env file (recommended):")
        print("  cp .env.example .env")
        print("  # Then edit .env and add your API key")
        print()
        print("Option 2: Set an environment variable:")
        print("  export YOUTUBE_API_KEY=your_key_here")
        print()
        print("Option 3: Pass it as an argument:")
        print("  python extract.py --api-key YOUR_KEY URL")
        print()
        print("Get a free key at: https://console.cloud.google.com/apis/credentials")
        sys.exit(1)

    url_type, identifier = parse_youtube_url(args.url)
    if not url_type:
        print(f"Error: Unrecognized YouTube URL format: {args.url}")
        print()
        print("Supported formats:")
        print("  youtube.com/@username")
        print("  youtube.com/c/channelname")
        print("  youtube.com/channel/CHANNEL_ID")
        print("  youtube.com/user/username")
        print("  youtube.com/watch?v=VIDEO_ID")
        print("  youtu.be/VIDEO_ID")
        sys.exit(1)

    try:
        channel_id = resolve_channel_id(url_type, identifier, api_key)
    except HTTPError as e:
        status = e.code
        body = e.read().decode()
        if status == 400:
            print("Error: Bad request — the URL may be malformed.")
            print(f"API response: {body}")
        elif status == 403:
            error_reason = ""
            try:
                error_reason = json.loads(body)["error"]["errors"][0]["reason"]
            except (KeyError, IndexError, ValueError):
                pass
            if error_reason == "quotaExceeded":
                print("Error: YouTube API daily quota exceeded (10,000 units/day).")
                print("Quota resets at midnight Pacific Time.")
                print(
                    "Check usage: https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas"
                )
            else:
                print("Error: API key is invalid or lacks permission.")
                print(
                    "Verify your key: https://console.cloud.google.com/apis/credentials"
                )
                print(
                    "Ensure YouTube Data API v3 is enabled: "
                    "https://console.cloud.google.com/apis/api/youtube.googleapis.com"
                )
        else:
            print(f"Error: YouTube API returned HTTP {status}.")
            print(f"Response: {body}")
        sys.exit(1)
    except URLError:
        print("Error: Could not connect to the YouTube API.")
        print("Check your internet connection and try again.")
        sys.exit(1)

    if not channel_id:
        print("Error: Could not resolve channel ID.")
        sys.exit(1)

    rss_url = RSS_TEMPLATE.format(channel_id)
    print(f"Channel ID:   {channel_id}")
    print(f"RSS Feed URL: {rss_url}")


if __name__ == "__main__":
    main()
