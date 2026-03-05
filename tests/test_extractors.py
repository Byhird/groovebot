"""Tests for extractors module."""

from unittest.mock import patch, Mock

import pytest

from groovebot.extractors import (
    _clean_youtube_title,
    _strip_metadata_from_title,
    extract_music_links,
    get_youtube_track_info,
)


class TestStripMetadataFromTitle:
    """Tests for _strip_metadata_from_title function."""

    def test_live_performance_with_location_and_date(self):
        title = "Men Without Hats – On Tuesday (Live in South Jordan, Utah | July 28, 2025)"
        result = _strip_metadata_from_title(title)
        assert result == "Men Without Hats – On Tuesday"

    def test_tv_appearance_with_year(self):
        title = "The Easybeats - Friday On My Mind (French TV, 1967) 1080p HD"
        result = _strip_metadata_from_title(title)
        assert result == "The Easybeats - Friday On My Mind"

    def test_lyric_video(self):
        title = "Dylan Gossett - Coal (Lyric Video)"
        result = _strip_metadata_from_title(title)
        assert result == "Dylan Gossett - Coal"

    def test_official_video(self):
        title = "Twenty One Pilots - Drag Path (Official Video)"
        result = _strip_metadata_from_title(title)
        assert result == "Twenty One Pilots - Drag Path"

    def test_music_video(self):
        title = "Artist - Song (Official Music Video)"
        result = _strip_metadata_from_title(title)
        assert result == "Artist - Song"

    def test_hd_quality_suffix(self):
        title = "Artist - Song 1080p HD"
        result = _strip_metadata_from_title(title)
        assert result == "Artist - Song"

    def test_remastered(self):
        title = "Artist - Song (Remastered)"
        result = _strip_metadata_from_title(title)
        assert result == "Artist - Song"

    def test_live_at_venue(self):
        title = "Artist - Song (Live at Madison Square Garden)"
        result = _strip_metadata_from_title(title)
        assert result == "Artist - Song"

    def test_acoustic_version(self):
        title = "Artist - Song (Acoustic Version)"
        result = _strip_metadata_from_title(title)
        assert result == "Artist - Song"

    def test_multiple_brackets(self):
        title = "Artist - Song (Official Video) [HD]"
        result = _strip_metadata_from_title(title)
        assert result == "Artist - Song"

    def test_no_metadata(self):
        title = "Artist - Song"
        result = _strip_metadata_from_title(title)
        assert result == "Artist - Song"

    def test_year_only(self):
        title = "Artist - Song (2024)"
        result = _strip_metadata_from_title(title)
        assert result == "Artist - Song"


class TestCleanYoutubeTitle:
    """Tests for _clean_youtube_title function."""

    def test_artist_dash_title_with_parenthetical(self):
        title = "Men Without Hats – On Tuesday (Live in South Jordan, Utah | July 28, 2025)"
        song, artist = _clean_youtube_title(title, None)
        assert song == "On Tuesday"
        assert artist == "Men Without Hats"

    def test_artist_dash_title_basic(self):
        title = "The Easybeats - Friday On My Mind (French TV, 1967) 1080p HD"
        song, artist = _clean_youtube_title(title, None)
        assert song == "Friday On My Mind"
        assert artist == "The Easybeats"

    def test_lyric_video(self):
        title = "Dylan Gossett - Coal (Lyric Video)"
        song, artist = _clean_youtube_title(title, None)
        assert song == "Coal"
        assert artist == "Dylan Gossett"

    def test_official_video(self):
        title = "Twenty One Pilots - Drag Path (Official Video)"
        song, artist = _clean_youtube_title(title, None)
        assert song == "Drag Path"
        assert artist == "Twenty One Pilots"

    def test_en_dash_separator(self):
        title = "Artist – Song Title"
        song, artist = _clean_youtube_title(title, None)
        assert song == "Song Title"
        assert artist == "Artist"

    def test_em_dash_separator(self):
        title = "Artist — Song Title"
        song, artist = _clean_youtube_title(title, None)
        assert song == "Song Title"
        assert artist == "Artist"

    def test_pipe_format(self):
        title = "Song Title | Artist Name"
        song, artist = _clean_youtube_title(title, None)
        assert song == "Song Title"
        assert artist == "Artist Name"

    def test_fallback_artist(self):
        title = "Just A Song Title"
        song, artist = _clean_youtube_title(title, "Fallback Artist")
        assert song == "Just A Song Title"
        assert artist == "Fallback Artist"


class TestExtractMusicLinks:
    """Tests for extract_music_links function."""

    def test_youtube_standard_url(self):
        links = extract_music_links("check this out https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert len(links) == 1
        assert links[0].source == "youtube"
        assert links[0].id == "dQw4w9WgXcQ"

    def test_youtube_short_url(self):
        links = extract_music_links("https://youtu.be/dQw4w9WgXcQ")
        assert len(links) == 1
        assert links[0].source == "youtube"

    def test_youtube_music_url(self):
        links = extract_music_links("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
        assert len(links) == 1
        assert links[0].source == "youtube"

    def test_spotify_url(self):
        links = extract_music_links("https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8")
        assert len(links) == 1
        assert links[0].source == "spotify"
        assert links[0].id == "4PTG3Z6ehGkBFwjybzWkR8"

    def test_no_links(self):
        links = extract_music_links("just a normal message")
        assert len(links) == 0

    def test_multiple_links(self):
        text = (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ "
            "https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8"
        )
        links = extract_music_links(text)
        assert len(links) == 2


class TestGetYoutubeTrackInfo:
    """Tests for get_youtube_track_info using mocked oEmbed responses."""

    @patch("groovebot.extractors.requests.get")
    def test_basic_artist_title(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "title": "The Easybeats - Friday On My Mind (French TV, 1967) 1080p HD",
            "author_name": "SomeChannel",
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        info = get_youtube_track_info("https://www.youtube.com/watch?v=test123")
        assert info is not None
        assert info.title == "Friday On My Mind"
        assert info.artist == "The Easybeats"
        assert info.source == "youtube"

    @patch("groovebot.extractors.requests.get")
    def test_fallback_to_author_name(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "title": "Friday On My Mind",
            "author_name": "The Easybeats",
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        info = get_youtube_track_info("https://www.youtube.com/watch?v=test123")
        assert info is not None
        assert info.title == "Friday On My Mind"
        assert info.artist == "The Easybeats"

    @patch("groovebot.extractors.requests.get")
    def test_no_title_returns_none(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = {"author_name": "SomeChannel"}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        info = get_youtube_track_info("https://www.youtube.com/watch?v=test123")
        assert info is None

    @patch("groovebot.extractors.requests.get")
    def test_http_error_returns_none(self, mock_get):
        mock_get.side_effect = Exception("HTTP 404")

        info = get_youtube_track_info("https://www.youtube.com/watch?v=test123")
        assert info is None

    @patch("groovebot.extractors.requests.get")
    def test_oembed_called_with_correct_params(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "title": "Artist - Song",
            "author_name": "Artist",
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        url = "https://www.youtube.com/watch?v=abc123"
        get_youtube_track_info(url)

        mock_get.assert_called_once_with(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            timeout=10,
        )
