"""Tests for extractors module."""

import pytest

from groovebot.extractors import _clean_youtube_title, _strip_metadata_from_title


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
