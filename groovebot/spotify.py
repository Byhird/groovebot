"""Spotify API client for searching tracks and managing playlists.

Note: This module uses direct Spotify API calls instead of the spotipy library.
As of late 2024, Spotify deprecated the /playlists/{id}/tracks endpoint in favour
of /playlists/{id}/items. The spotipy library still uses the old endpoint, causing
403 errors for apps in development mode.
"""

import base64
import logging
import time

import requests

from .config import Config

logger = logging.getLogger(__name__)

SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


class SpotifyAuth:
    """Handles Spotify OAuth token refresh."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self._access_token: str | None = None
        self._expires_at: float = 0

    def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token

        # Refresh the token
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        resp = requests.post(
            SPOTIFY_TOKEN_URL,
            headers={"Authorization": f"Basic {auth_header}"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        self._access_token = data["access_token"]
        self._expires_at = time.time() + data["expires_in"]

        return self._access_token


class SpotifyClient:
    """Client for Spotify API operations."""

    def __init__(self, config: Config):
        """Initialize the Spotify client.

        Args:
            config: Application configuration with Spotify credentials.
        """
        self.config = config
        self.playlist_id = config.spotify_playlist_id
        self._auth = SpotifyAuth(
            client_id=config.spotify_client_id,
            client_secret=config.spotify_client_secret,
            refresh_token=config.spotify_refresh_token,
        )

    def _get_headers(self) -> dict:
        """Get authorization headers for API calls."""
        return {"Authorization": f"Bearer {self._auth.get_access_token()}"}

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Make a GET request to the Spotify API."""
        url = f"{SPOTIFY_API_BASE}/{endpoint}"
        resp = requests.get(url, headers=self._get_headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, data: dict | None = None) -> dict | None:
        """Make a POST request to the Spotify API."""
        url = f"{SPOTIFY_API_BASE}/{endpoint}"
        resp = requests.post(url, headers=self._get_headers(), json=data)
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def get_track(self, track_id: str) -> dict | None:
        """Get track info by Spotify track ID.

        Args:
            track_id: Spotify track ID.

        Returns:
            Track dict or None if not found.
        """
        try:
            return self._get(f"tracks/{track_id}")
        except Exception as e:
            logger.error(f"Failed to get track {track_id}: {e}")
            return None

    def search_track(self, title: str, artist: str | None = None) -> dict | None:
        """Search for a track on Spotify.

        Args:
            title: Track title to search for.
            artist: Optional artist name to narrow search.

        Returns:
            Best matching track dict, or None if no results.
        """
        query = title
        if artist and artist != "Unknown":
            query = f"track:{title} artist:{artist}"

        try:
            results = self._get("search", {"q": query, "type": "track", "limit": 1})
            tracks = results.get("tracks", {}).get("items", [])
            return tracks[0] if tracks else None
        except Exception as e:
            logger.error(f"Failed to search for track '{query}': {e}")
            return None

    def add_to_playlist(self, track_id: str) -> bool:
        """Add a track to the configured playlist.

        Args:
            track_id: Spotify track ID to add.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Check if track is already in playlist
            if self._is_track_in_playlist(track_id):
                logger.info(f"Track {track_id} already in playlist")
                return True

            self._post(
                f"playlists/{self.playlist_id}/items",
                {"uris": [f"spotify:track:{track_id}"]},
            )
            logger.info(f"Added track {track_id} to playlist {self.playlist_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add track to playlist: {e}")
            return False

    def _is_track_in_playlist(self, track_id: str) -> bool:
        """Check if a track is already in the playlist.

        Args:
            track_id: Spotify track ID to check.

        Returns:
            True if track is in playlist, False otherwise.
        """
        try:
            offset = 0
            limit = 100

            while True:
                results = self._get(
                    f"playlists/{self.playlist_id}/items",
                    {"offset": offset, "limit": limit, "fields": "items(track(id))"},
                )

                items = results.get("items", [])
                for item in items:
                    track = item.get("track")
                    if track and track.get("id") == track_id:
                        return True

                if len(items) < limit:
                    break

                offset += limit

            return False
        except Exception as e:
            logger.warning(f"Failed to check playlist for duplicates: {e}")
            return False  # Proceed with add attempt

    def get_track_display_name(self, track: dict) -> str:
        """Format track info for display.

        Args:
            track: Spotify track dict.

        Returns:
            Formatted string like "Artist - Track Name".
        """
        artists = ", ".join(a["name"] for a in track.get("artists", []))
        name = track.get("name", "Unknown")
        return f"{artists} - {name}" if artists else name
