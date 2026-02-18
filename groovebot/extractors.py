"""URL extraction and metadata fetching for YouTube and Spotify links."""

import logging
import re
from dataclasses import dataclass

import yt_dlp

logger = logging.getLogger(__name__)

# Regex patterns for music links
YOUTUBE_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|music\.youtube\.com/watch\?v=)"
    r"([a-zA-Z0-9_-]{11})"
)
SPOTIFY_TRACK_PATTERN = re.compile(
    r"(?:https?://)?(?:open\.)?spotify\.com/track/([a-zA-Z0-9]{22})"
)


@dataclass
class MusicLink:
    """Represents a parsed music link."""

    url: str
    source: str  # "youtube" or "spotify"
    id: str  # video ID or track ID


@dataclass
class TrackInfo:
    """Metadata about a track."""

    title: str
    artist: str
    source: str


def extract_music_links(text: str) -> list[MusicLink]:
    """Extract YouTube and Spotify links from text.

    Args:
        text: Message text to search for links.

    Returns:
        List of MusicLink objects found in the text.
    """
    links = []

    for match in YOUTUBE_PATTERN.finditer(text):
        video_id = match.group(1)
        # Reconstruct a clean URL
        url = f"https://www.youtube.com/watch?v={video_id}"
        links.append(MusicLink(url=url, source="youtube", id=video_id))

    for match in SPOTIFY_TRACK_PATTERN.finditer(text):
        track_id = match.group(1)
        url = f"https://open.spotify.com/track/{track_id}"
        links.append(MusicLink(url=url, source="spotify", id=track_id))

    return links


def get_youtube_track_info(url: str) -> TrackInfo | None:
    """Fetch track metadata from a YouTube video.

    Args:
        url: YouTube video URL.

    Returns:
        TrackInfo if metadata was successfully extracted, None otherwise.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if not info:
                return None

            # yt-dlp often extracts artist/track for music videos
            artist = info.get("artist") or info.get("creator") or info.get("uploader")
            title = info.get("track") or info.get("title")

            if not title:
                return None

            # Clean up the title if no track metadata available
            if not info.get("track"):
                title, artist = _clean_youtube_title(title, artist)

            return TrackInfo(
                title=title,
                artist=artist or "Unknown",
                source="youtube",
            )

    except Exception as e:
        logger.error(f"Failed to extract YouTube metadata: {e}")
        return None


def _clean_youtube_title(title: str, fallback_artist: str | None) -> tuple[str, str | None]:
    """Attempt to extract artist and song from YouTube video title.

    Common formats:
    - "Artist - Song Title"
    - "Artist - Song Title (Official Video)"
    - "Song Title | Artist"

    Args:
        title: Raw video title.
        fallback_artist: Artist to use if not found in title.

    Returns:
        Tuple of (cleaned_title, artist).
    """
    # Remove common suffixes
    clean = re.sub(
        r"\s*[\(\[]?\s*(?:official\s+)?(?:music\s+)?(?:video|audio|lyrics?|hd|hq|4k|remaster(?:ed)?)"
        r"\s*[\)\]]?\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    # Try "Artist - Title" format
    if " - " in clean:
        parts = clean.split(" - ", 1)
        return parts[1].strip(), parts[0].strip()

    # Try "Title | Artist" format
    if " | " in clean:
        parts = clean.split(" | ", 1)
        return parts[0].strip(), parts[1].strip()

    return clean.strip(), fallback_artist
