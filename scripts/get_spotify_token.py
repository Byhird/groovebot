#!/usr/bin/env python3
"""One-time script to obtain Spotify refresh token.

Run this script locally to authorize the bot and obtain a refresh token.
You only need to do this once.

Usage:
    1. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables
    2. Run: python scripts/get_spotify_token.py
    3. Follow the browser authorization flow
    4. Copy the refresh token to your .env file
"""

import os
import sys

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private"
REDIRECT_URI = "http://127.0.0.1:8888/callback"


def main():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Error: Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables")
        sys.exit(1)

    print("Opening browser for Spotify authorization...")
    print("(If browser doesn't open, check the terminal for a URL)\n")

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        open_browser=True,
    )

    # This will trigger the browser auth flow
    sp = Spotify(auth_manager=auth_manager)

    # Get user info to confirm auth worked
    user = sp.current_user()
    print(f"\n✓ Authorized as: {user['display_name']} ({user['id']})")

    # Get the refresh token
    token_info = auth_manager.get_cached_token()
    refresh_token = token_info["refresh_token"]

    print(f"\n{'='*60}")
    print("Add this to your .env file:")
    print(f"{'='*60}")
    print(f"SPOTIFY_REFRESH_TOKEN={refresh_token}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
