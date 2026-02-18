"""Spotify API client for searching tracks and managing playlists."""

import logging
import time

import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from .config import Config

logger = logging.getLogger(__name__)


class RefreshTokenAuth:
    """Simple auth manager that uses a refresh token."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self._token_info = None

        # Use SpotifyOAuth just for token refresh
        self._oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="playlist-modify-public playlist-modify-private playlist-read-private",
            open_browser=False,
        )

    def get_access_token(self, as_dict: bool = True, check_cache: bool = True):
        """Get a valid access token, refreshing if necessary."""
        if self._token_info and not self._is_token_expired():
            return self._token_info if as_dict else self._token_info["access_token"]

        # Refresh the token
        self._token_info = self._oauth.refresh_access_token(self.refresh_token)
        return self._token_info if as_dict else self._token_info["access_token"]

    def _is_token_expired(self) -> bool:
        if not self._token_info:
            return True
        # Add 60 second buffer
        return self._token_info["expires_at"] - 60 < time.time()


class SpotifyClient:
    """Wrapper around spotipy for track search and playlist management."""

    def __init__(self, config: Config):
        """Initialize the Spotify client.

        Args:
            config: Application configuration with Spotify credentials.
        """
        self.config = config
        self.playlist_id = config.spotify_playlist_id

        # Use custom auth manager with refresh token
        auth_manager = RefreshTokenAuth(
            client_id=config.spotify_client_id,
            client_secret=config.spotify_client_secret,
            refresh_token=config.spotify_refresh_token,
        )

        self.client = spotipy.Spotify(auth_manager=auth_manager)
        self._auth_manager = auth_manager

    def _get_headers(self) -> dict:
        """Get authorization headers for direct API calls."""
        token = self._auth_manager.get_access_token(as_dict=False)
        return {"Authorization": f"Bearer {token}"}

    def get_track(self, track_id: str) -> dict | None:
        """Get track info by Spotify track ID.

        Args:
            track_id: Spotify track ID.

        Returns:
            Track dict or None if not found.
        """
        try:
            return self.client.track(track_id)
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
            results = self.client.search(q=query, type="track", limit=1)
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

            # Use direct API call with /items endpoint (spotipy uses deprecated /tracks)
            url = f"https://api.spotify.com/v1/playlists/{self.playlist_id}/items"
            data = {"uris": [f"spotify:track:{track_id}"]}
            resp = requests.post(url, headers=self._get_headers(), json=data)
            resp.raise_for_status()

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
                # Use direct API call with /items endpoint (spotipy uses deprecated /tracks)
                url = f"https://api.spotify.com/v1/playlists/{self.playlist_id}/items"
                params = {
                    "offset": offset,
                    "limit": limit,
                    "fields": "items(track(id)),total",
                }
                resp = requests.get(url, headers=self._get_headers(), params=params)
                resp.raise_for_status()
                results = resp.json()

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
