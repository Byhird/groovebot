# Groovebot

A Slack bot that watches channels for YouTube and Spotify links and adds them to a shared Spotify playlist.

***Basically entirely vibe-coded, fair warning!***

## Features

- Monitors Slack channels for YouTube and Spotify track links
- Extracts song metadata from YouTube videos using yt-dlp
- Searches Spotify for matching tracks
- Adds tracks to a configured playlist
- `@groovebot add: Artist - Song Name` — manually add a track by name
- `@groovebot help` — display usage info and reaction meanings
- Reacts to messages with ✅ on success or ❓/❌ on failure
- Duplicate detection (won't add the same track twice)

## Setup

### 1. Create a Slack App

**Option A: Using the manifest (recommended)**

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From an app manifest**
3. Select your workspace and paste the contents of `slack-app-manifest.yml`
4. Review and click **Create**

**Option B: Manual setup**

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Under **OAuth & Permissions**, add these Bot Token Scopes:
   - `app_mentions:read` - Receive @groovebot mentions
   - `channels:history` - Read messages in public channels
   - `groups:history` - Read messages in private channels (if needed)
   - `reactions:write` - Add reactions to messages
   - `chat:write` - Post messages (required for `DEBUG_MESSAGES` feature and mention replies)
3. Under **Socket Mode**, enable Socket Mode
4. Under **Event Subscriptions**, enable events and subscribe to:
   - `app_mention` - @groovebot mentions
   - `message.channels` - Messages in public channels
   - `message.groups` - Messages in private channels (if needed)

**After creating the app:**

1. Generate an **App-Level Token**: Settings → Basic Information → App-Level Tokens → Create with `connections:write` scope
2. **Install to workspace**: Settings → Install App → Install
3. **Invite the bot** to the channel(s) you want it to monitor

Copy these tokens:
- **Bot Token** (`xoxb-...`) from OAuth & Permissions
- **App Token** (`xapp-...`) from App-Level Tokens

### 2. Create a Spotify App

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add `http://127.0.0.1:8888/callback` as a Redirect URI
4. Copy the **Client ID** and **Client Secret**

### 3. Get Spotify Refresh Token

Run the helper script to authorize the bot:

```bash
pip install requests
export SPOTIFY_CLIENT_ID=your-client-id
export SPOTIFY_CLIENT_SECRET=your-client-secret
python scripts/get_spotify_token.py
```

This will open a browser for authorization. After authorizing, copy the refresh token.

### 4. Get Your Playlist ID

Find your playlist in Spotify, click Share → Copy link. The ID is in the URL:
```
https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
                                    ^^^^^^^^^^^^^^^^^^^^^^
                                    This is the playlist ID
```

### 5. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

### 6. Run

**With Docker (recommended):**

```bash
docker compose up -d
```

**Without Docker:**

```bash
pip install -r requirements.txt
python -m groovebot.main
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Slack bot token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | Yes | Slack app token (`xapp-...`) |
| `SPOTIFY_CLIENT_ID` | Yes | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | Yes | Spotify app client secret |
| `SPOTIFY_REFRESH_TOKEN` | Yes | Spotify refresh token (from setup script) |
| `SPOTIFY_PLAYLIST_ID` | Yes | Target playlist ID |
| `SLACK_CHANNEL_IDS` | No | Comma-separated channel IDs to monitor (monitors all if not set) |

## How It Works

1. Bot connects to Slack via Socket Mode (no public URL needed)
2. Listens for messages containing YouTube or Spotify links
3. For YouTube links: extracts metadata with yt-dlp, searches Spotify
4. For Spotify links: uses the track ID directly
5. Adds the track to the playlist and reacts to the message

### Mention Commands

Users can also interact with Groovebot directly via @mentions:

- `@groovebot add: Artist - Song Name` — searches Spotify for the given artist and song and adds the best match to the playlist.
- `@groovebot help` — replies with a summary of features and what the reaction emojis mean.

## Spotify API Note

As of late 2024, Spotify deprecated the `/playlists/{id}/tracks` endpoint in favour of `/playlists/{id}/items`. The popular `spotipy` library still uses the deprecated endpoint, which results in **403 Forbidden errors** for apps in development mode.

This project uses direct Spotify API calls with the correct `/items` endpoint, avoiding this issue entirely.

## Troubleshooting

### 403 Forbidden on playlist operations

1. **Check your Spotify account**: The app owner must have Spotify Premium for development mode apps
2. **Add yourself to User Management**: In the Spotify Developer Dashboard, go to your app → User Management and add your Spotify account email
3. **Verify scopes**: Ensure your refresh token was generated with `playlist-modify-public`, `playlist-modify-private`, and `playlist-read-private` scopes
4. **Revoke and re-authorize**: If you changed scopes, revoke the app at https://www.spotify.com/account/apps/ and re-run the token script

### "Couldn't write token to cache" warning

This warning from spotipy can be ignored—this project doesn't use spotipy or token caching.

## License

MIT
