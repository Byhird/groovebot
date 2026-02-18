"""Configuration management for Groovebot."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    slack_bot_token: str
    slack_app_token: str
    spotify_client_id: str
    spotify_client_secret: str
    spotify_refresh_token: str
    spotify_playlist_id: str
    slack_channel_ids: list[str] | None = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Raises:
            ValueError: If required environment variables are missing.
        """
        load_dotenv()

        required_vars = [
            "SLACK_BOT_TOKEN",
            "SLACK_APP_TOKEN",
            "SPOTIFY_CLIENT_ID",
            "SPOTIFY_CLIENT_SECRET",
            "SPOTIFY_REFRESH_TOKEN",
            "SPOTIFY_PLAYLIST_ID",
        ]

        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        channel_ids_raw = os.getenv("SLACK_CHANNEL_IDS", "").strip()
        channel_ids = (
            [c.strip() for c in channel_ids_raw.split(",") if c.strip()]
            if channel_ids_raw
            else None
        )

        return cls(
            slack_bot_token=os.environ["SLACK_BOT_TOKEN"],
            slack_app_token=os.environ["SLACK_APP_TOKEN"],
            spotify_client_id=os.environ["SPOTIFY_CLIENT_ID"],
            spotify_client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            spotify_refresh_token=os.environ["SPOTIFY_REFRESH_TOKEN"],
            spotify_playlist_id=os.environ["SPOTIFY_PLAYLIST_ID"],
            slack_channel_ids=channel_ids,
        )
