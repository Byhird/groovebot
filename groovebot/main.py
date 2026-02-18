"""Main entry point for Groovebot."""

import logging
import sys

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .config import Config
from .handlers import register_handlers
from .spotify import SpotifyClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the Groovebot application."""
    logger.info("Starting Groovebot...")

    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize Slack app
    app = App(token=config.slack_bot_token)

    # Initialize Spotify client
    try:
        spotify = SpotifyClient(config)
        logger.info("Spotify client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Spotify client: {e}")
        sys.exit(1)

    # Register handlers
    register_handlers(app, config, spotify)

    # Start Socket Mode handler
    handler = SocketModeHandler(app, config.slack_app_token)

    logger.info("Groovebot is running! Listening for music links...")

    try:
        handler.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
