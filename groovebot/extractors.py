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
    clean = _strip_metadata_from_title(title)

    # Try "Artist - Title" format (also handle en-dash and em-dash)
    if " - " in clean:
        parts = clean.split(" - ", 1)
        return parts[1].strip(), parts[0].strip()
    if " – " in clean:  # en-dash
        parts = clean.split(" – ", 1)
        return parts[1].strip(), parts[0].strip()
    if " — " in clean:  # em-dash
        parts = clean.split(" — ", 1)
        return parts[1].strip(), parts[0].strip()

    # Try "Title | Artist" format
    if " | " in clean:
        parts = clean.split(" | ", 1)
        return parts[0].strip(), parts[1].strip()

    return clean.strip(), fallback_artist


def _strip_metadata_from_title(title: str) -> str:
    """Remove parenthetical/bracketed metadata from a YouTube title.

    Strips things like:
    - (Official Video), (Lyric Video), (Music Video)
    - (Live in City, State | Date)
    - (French TV, 1967)
    - [HD], [4K], [Remastered]
    - 1080p HD, etc.

    Args:
        title: Raw video title.

    Returns:
        Title with metadata stripped.
    """
    clean = title

    # Remove parenthetical/bracketed content containing metadata keywords
    # This handles: (Live in ...), (Official Video), (Lyric Video), (French TV, 1967), etc.
    metadata_pattern = re.compile(
        r"\s*[\(\[]\s*"
        r"(?:"
        r"live\s+(?:in|at|from|on)\s+[^\)\]]+"
        r"|[^\)\]]*?\b(?:official|music|lyric|lyrics|video|audio|hd|hq|4k|1080p|720p|remaster(?:ed)?|tv|version|edit|remix|cover|acoustic|unplugged|session|performance|concert|tour)\b[^\)\]]*"
        r"|[^\)\]]*\b\d{4}\b[^\)\]]*"  # anything with a year like (1967) or (July 28, 2025)
        r")"
        r"\s*[\)\]]",
        flags=re.IGNORECASE,
    )
    clean = metadata_pattern.sub("", clean)

    # Remove standalone quality suffixes without brackets
    clean = re.sub(
        r"\s+(?:1080p|720p|480p|4k|hd|hq)(?:\s+hd)?\s*$",
        "",
        clean,
        flags=re.IGNORECASE,
    )

    # Clean up any double spaces and trim
    clean = re.sub(r"\s{2,}", " ", clean).strip()

    return clean
