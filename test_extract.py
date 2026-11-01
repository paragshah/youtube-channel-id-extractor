"""Tests for extract.py — YouTube channel ID extractor."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from extract import main, parse_youtube_url, resolve_channel_id


# ---------------------------------------------------------------------------
# parse_youtube_url — pure URL parsing, no network calls
# ---------------------------------------------------------------------------

class TestParseYoutubeUrl:
    """Test all supported YouTube URL formats."""

    # --- @handle URLs ---

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/@mkbhd",
        "https://youtube.com/@mkbhd",
        "http://www.youtube.com/@mkbhd",
        "https://m.youtube.com/@mkbhd",
        "youtube.com/@mkbhd",
        "www.youtube.com/@mkbhd",
        "https://www.youtube.com/@mkbhd/",
    ])
    def test_handle_url(self, url):
        assert parse_youtube_url(url) == ("handle", "mkbhd")

    def test_handle_with_subpath(self):
        # Trailing path segments after handle (e.g. /videos) are included
        url_type, identifier = parse_youtube_url("https://www.youtube.com/@mkbhd/videos")
        assert url_type == "handle"
        assert identifier.startswith("mkbhd")

    # --- /channel/ID URLs ---

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw",
        "https://youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw",
        "http://youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw",
        "https://m.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw",
        "youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw",
        "https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw/",
    ])
    def test_channel_id_url(self, url):
        assert parse_youtube_url(url) == ("channel_id", "UCXuqSBlHAE6Xw-yeJA0Tunw")

    # --- /c/custom URLs ---

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/c/LinusTechTips",
        "https://youtube.com/c/LinusTechTips",
        "youtube.com/c/LinusTechTips",
        "https://www.youtube.com/c/LinusTechTips/",
    ])
    def test_custom_url(self, url):
        assert parse_youtube_url(url) == ("custom", "LinusTechTips")

    # --- /user/username URLs ---

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/user/PewDiePie",
        "https://youtube.com/user/PewDiePie",
        "youtube.com/user/PewDiePie",
        "https://www.youtube.com/user/PewDiePie/",
    ])
    def test_user_url(self, url):
        assert parse_youtube_url(url) == ("user", "PewDiePie")

    # --- /watch?v= URLs ---

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ",
    ])
    def test_watch_url(self, url):
        assert parse_youtube_url(url) == ("video", "dQw4w9WgXcQ")

    def test_watch_url_with_extra_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        assert parse_youtube_url(url) == ("video", "dQw4w9WgXcQ")

    # --- youtu.be short URLs ---

    @pytest.mark.parametrize("url", [
        "https://youtu.be/dQw4w9WgXcQ",
        "http://youtu.be/dQw4w9WgXcQ",
        "youtu.be/dQw4w9WgXcQ",
    ])
    def test_short_url(self, url):
        assert parse_youtube_url(url) == ("video", "dQw4w9WgXcQ")

    def test_short_url_with_timestamp(self):
        url = "https://youtu.be/dQw4w9WgXcQ?t=42"
        assert parse_youtube_url(url) == ("video", "dQw4w9WgXcQ")

    # --- URLs without scheme ---

    def test_no_scheme_prepends_https(self):
        assert parse_youtube_url("youtube.com/@mkbhd") == ("handle", "mkbhd")

    # --- Unrecognized / invalid URLs ---

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/",
        "https://www.youtube.com",
        "https://example.com/watch?v=abc",
        "https://vimeo.com/12345",
        "not-a-url",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/results?search_query=test",
    ])
    def test_unrecognized_url_returns_none(self, url):
        assert parse_youtube_url(url) == (None, None)

    def test_empty_handle(self):
        assert parse_youtube_url("https://www.youtube.com/@") == (None, None)

    def test_empty_channel_path(self):
        assert parse_youtube_url("https://www.youtube.com/channel/") == (None, None)

    def test_empty_user_path(self):
        assert parse_youtube_url("https://www.youtube.com/user/") == (None, None)

    def test_empty_custom_path(self):
        assert parse_youtube_url("https://www.youtube.com/c/") == (None, None)


# ---------------------------------------------------------------------------
# resolve_channel_id — mock API calls
# ---------------------------------------------------------------------------

FAKE_API_KEY = "fake-api-key"


def _mock_api_response(items):
    """Build a minimal YouTube API-style response dict."""
    return {"items": items}


class TestResolveChannelId:
    """Test channel ID resolution with mocked API responses."""

    @patch("extract.api_get")
    def test_channel_id_found(self, mock_api):
        mock_api.return_value = _mock_api_response([{"id": "UCxyz"}])
        result = resolve_channel_id("channel_id", "UCxyz", FAKE_API_KEY)
        assert result == "UCxyz"
        mock_api.assert_called_once_with(
            "channels", {"part": "snippet", "id": "UCxyz"}, FAKE_API_KEY
        )

    @patch("extract.api_get")
    def test_channel_id_not_found_exits(self, mock_api):
        mock_api.return_value = _mock_api_response([])
        with pytest.raises(SystemExit, match="1"):
            resolve_channel_id("channel_id", "UCbad", FAKE_API_KEY)

    @patch("extract.api_get")
    def test_handle_found(self, mock_api):
        mock_api.return_value = _mock_api_response([{"id": "UCabc"}])
        result = resolve_channel_id("handle", "mkbhd", FAKE_API_KEY)
        assert result == "UCabc"
        mock_api.assert_called_once_with(
            "channels", {"part": "snippet", "forHandle": "mkbhd"}, FAKE_API_KEY
        )

    @patch("extract.api_get")
    def test_handle_not_found_exits(self, mock_api):
        mock_api.return_value = _mock_api_response([])
        with pytest.raises(SystemExit, match="1"):
            resolve_channel_id("handle", "nonexistent", FAKE_API_KEY)

    @patch("extract.api_get")
    def test_user_found(self, mock_api):
        mock_api.return_value = _mock_api_response([{"id": "UCdef"}])
        result = resolve_channel_id("user", "PewDiePie", FAKE_API_KEY)
        assert result == "UCdef"
        mock_api.assert_called_once_with(
            "channels", {"part": "snippet", "forUsername": "PewDiePie"}, FAKE_API_KEY
        )

    @patch("extract.api_get")
    def test_user_not_found_exits(self, mock_api):
        mock_api.return_value = _mock_api_response([])
        with pytest.raises(SystemExit, match="1"):
            resolve_channel_id("user", "nobody12345", FAKE_API_KEY)

    @patch("extract.api_get")
    def test_custom_resolved_via_handle(self, mock_api):
        mock_api.return_value = _mock_api_response([{"id": "UCghi"}])
        result = resolve_channel_id("custom", "LinusTechTips", FAKE_API_KEY)
        assert result == "UCghi"

    @patch("extract.api_get")
    def test_custom_falls_back_to_search(self, mock_api):
        mock_api.side_effect = [
            _mock_api_response([]),  # forHandle miss
            _mock_api_response([{"snippet": {"channelId": "UCfallback"}}]),  # search hit
        ]
        result = resolve_channel_id("custom", "OldCustomName", FAKE_API_KEY)
        assert result == "UCfallback"
        assert mock_api.call_count == 2

    @patch("extract.api_get")
    def test_custom_not_found_exits(self, mock_api):
        mock_api.side_effect = [
            _mock_api_response([]),  # forHandle miss
            _mock_api_response([]),  # search miss
        ]
        with pytest.raises(SystemExit, match="1"):
            resolve_channel_id("custom", "GhostChannel", FAKE_API_KEY)

    @patch("extract.api_get")
    def test_video_found(self, mock_api):
        mock_api.return_value = _mock_api_response(
            [{"snippet": {"channelId": "UCvid"}}]
        )
        result = resolve_channel_id("video", "dQw4w9WgXcQ", FAKE_API_KEY)
        assert result == "UCvid"
        mock_api.assert_called_once_with(
            "videos", {"part": "snippet", "id": "dQw4w9WgXcQ"}, FAKE_API_KEY
        )

    @patch("extract.api_get")
    def test_video_not_found_exits(self, mock_api):
        mock_api.return_value = _mock_api_response([])
        with pytest.raises(SystemExit, match="1"):
            resolve_channel_id("video", "badVideoId", FAKE_API_KEY)

    def test_unknown_url_type_returns_none(self):
        result = resolve_channel_id("unknown", "whatever", FAKE_API_KEY)
        assert result is None


# ---------------------------------------------------------------------------
# main() — CLI integration tests
# ---------------------------------------------------------------------------

class TestMainCLI:
    """End-to-end tests for the CLI entry point with mocked API."""

    @patch("extract.api_get")
    def test_successful_output(self, mock_api, capsys, monkeypatch):
        mock_api.return_value = _mock_api_response([{"id": "UCtest123"}])
        monkeypatch.setenv("YOUTUBE_API_KEY", FAKE_API_KEY)
        monkeypatch.setattr(sys, "argv", ["extract.py", "https://www.youtube.com/channel/UCtest123"])

        main()

        out = capsys.readouterr().out
        assert "UCtest123" in out
        assert "https://www.youtube.com/feeds/videos.xml?channel_id=UCtest123" in out

    @patch("os.path.isfile", return_value=False)
    def test_missing_api_key_exits(self, mock_isfile, capsys, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        monkeypatch.setattr(sys, "argv", ["extract.py", "https://www.youtube.com/@test"])

        with pytest.raises(SystemExit, match="1"):
            main()

        assert "No API key" in capsys.readouterr().out

    def test_unrecognized_url_exits(self, capsys, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", FAKE_API_KEY)
        monkeypatch.setattr(sys, "argv", ["extract.py", "https://example.com/notYouTube"])

        with pytest.raises(SystemExit, match="1"):
            main()

        assert "Unrecognized YouTube URL" in capsys.readouterr().out

    @patch("extract.api_get")
    def test_api_key_from_cli_arg(self, mock_api, capsys, monkeypatch):
        mock_api.return_value = _mock_api_response([{"id": "UCarg"}])
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        monkeypatch.setattr(
            sys, "argv",
            ["extract.py", "--api-key", "cli-key", "https://www.youtube.com/channel/UCarg"],
        )

        main()

        # Verify the CLI-provided key was forwarded
        call_args = mock_api.call_args
        assert call_args[0][2] == "cli-key"

    @patch("extract.api_get")
    def test_video_url_resolves_channel(self, mock_api, capsys, monkeypatch):
        mock_api.return_value = _mock_api_response(
            [{"snippet": {"channelId": "UCfromVideo"}}]
        )
        monkeypatch.setenv("YOUTUBE_API_KEY", FAKE_API_KEY)
        monkeypatch.setattr(sys, "argv", ["extract.py", "https://youtu.be/dQw4w9WgXcQ"])

        main()

        out = capsys.readouterr().out
        assert "UCfromVideo" in out
        assert "feeds/videos.xml?channel_id=UCfromVideo" in out

    @patch("extract.urlopen")
    def test_http_403_invalid_key(self, mock_urlopen, capsys, monkeypatch):
        from urllib.error import HTTPError
        from io import BytesIO

        error_body = json.dumps(
            {"error": {"errors": [{"reason": "keyInvalid"}]}}
        ).encode()
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com", code=403, msg="Forbidden",
            hdrs={}, fp=BytesIO(error_body),
        )
        monkeypatch.setenv("YOUTUBE_API_KEY", FAKE_API_KEY)
        monkeypatch.setattr(sys, "argv", ["extract.py", "https://www.youtube.com/@test"])

        with pytest.raises(SystemExit, match="1"):
            main()

        assert "invalid or lacks permission" in capsys.readouterr().out

    @patch("extract.urlopen")
    def test_http_403_quota_exceeded(self, mock_urlopen, capsys, monkeypatch):
        from urllib.error import HTTPError
        from io import BytesIO

        error_body = json.dumps(
            {"error": {"errors": [{"reason": "quotaExceeded"}]}}
        ).encode()
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com", code=403, msg="Forbidden",
            hdrs={}, fp=BytesIO(error_body),
        )
        monkeypatch.setenv("YOUTUBE_API_KEY", FAKE_API_KEY)
        monkeypatch.setattr(sys, "argv", ["extract.py", "https://www.youtube.com/@test"])

        with pytest.raises(SystemExit, match="1"):
            main()

        assert "quota exceeded" in capsys.readouterr().out

    @patch("extract.urlopen")
    def test_network_error(self, mock_urlopen, capsys, monkeypatch):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Name resolution failed")
        monkeypatch.setenv("YOUTUBE_API_KEY", FAKE_API_KEY)
        monkeypatch.setattr(sys, "argv", ["extract.py", "https://www.youtube.com/@test"])

        with pytest.raises(SystemExit, match="1"):
            main()

        assert "Could not connect" in capsys.readouterr().out
