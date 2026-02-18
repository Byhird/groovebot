#!/usr/bin/env python3
"""One-time script to obtain Spotify refresh token.

Run this script locally to authorize the bot and obtain a refresh token.
You only need to do this once.

Usage:
    1. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables
    2. Run: python scripts/get_spotify_token.py
    3. Follow the browser authorization flow
    4. Copy the refresh token to your .env file

Requirements:
    pip install requests
"""

import base64
import os
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlencode, urlparse

import requests

SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

# Will be set by the callback handler
auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    """Handle the OAuth callback from Spotify."""

    def do_GET(self):
        global auth_code
        query = parse_qs(urlparse(self.path).query)

        if "code" in query:
            auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization successful!</h1>")
            self.wfile.write(b"<p>You can close this window.</p></body></html>")
        else:
            error = query.get("error", ["Unknown error"])[0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h1>Error: {error}</h1></body></html>".encode())

    def log_message(self, format, *args):
        pass  # Suppress server logs


def main():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Error: Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables")
        sys.exit(1)

    # Build authorization URL
    auth_params = urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
    })
    auth_url = f"{AUTH_URL}?{auth_params}"

    print("Opening browser for Spotify authorization...")
    print(f"(If browser doesn't open, visit: {auth_url})\n")
    webbrowser.open(auth_url)

    # Start local server to receive callback
    server = HTTPServer(("127.0.0.1", 8888), CallbackHandler)
    server.handle_request()  # Handle single request

    if not auth_code:
        print("Error: No authorization code received")
        sys.exit(1)

    # Exchange code for tokens
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        TOKEN_URL,
        headers={"Authorization": f"Basic {auth_header}"},
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": REDIRECT_URI,
        },
    )

    if resp.status_code != 200:
        print(f"Error exchanging code for token: {resp.text}")
        sys.exit(1)

    token_data = resp.json()
    refresh_token = token_data["refresh_token"]
    access_token = token_data["access_token"]

    # Get user info to confirm auth worked
    user_resp = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user = user_resp.json()
    print(f"\n✓ Authorized as: {user.get('display_name', 'Unknown')} ({user['id']})")

    print(f"\n{'='*60}")
    print("Add this to your .env file:")
    print(f"{'='*60}")
    print(f"SPOTIFY_REFRESH_TOKEN={refresh_token}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
