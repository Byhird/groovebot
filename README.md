# Groovebot

A Slack bot that watches channels for YouTube and Spotify links and adds them to a shared Spotify playlist.

## Features

- Monitors Slack channels for YouTube and Spotify track links
- Extracts song metadata from YouTube videos using yt-dlp
- Searches Spotify for matching tracks
- Adds tracks to a configured playlist
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
   - `channels:history` - Read messages in public channels
   - `groups:history` - Read messages in private channels (if needed)
   - `reactions:write` - Add reactions to messages
3. Under **Socket Mode**, enable Socket Mode
4. Under **Event Subscriptions**, enable events and subscribe to:
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
3. Add `http://localhost:8888/callback` as a Redirect URI
4. Copy the **Client ID** and **Client Secret**

### 3. Get Spotify Refresh Token

Run the helper script to authorize the bot:

```bash
pip install spotipy
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

## License

MIT
