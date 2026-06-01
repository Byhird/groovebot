"""Startup backfill: scan last week's messages for unprocessed music links."""

import logging
import time
from datetime import datetime, timedelta, timezone

from slack_sdk.errors import SlackApiError
from slack_sdk.web.client import WebClient

from .config import Config
from .extractors import extract_music_links
from .handlers import MessageHandler
from .spotify import SpotifyClient

logger = logging.getLogger(__name__)


class BackfillRunner:
    """Scans Slack channel history and processes music links the bot missed."""

    def __init__(
        self,
        config: Config,
        spotify: SpotifyClient,
        message_handler: MessageHandler,
        client: WebClient,
    ):
        self.config = config
        self.spotify = spotify
        self.message_handler = message_handler
        self.client = client
        self._bot_user_id: str | None = None

    def run(self) -> None:
        """Execute the backfill across all target channels."""
        channels = self._get_target_channels()
        if not channels:
            logger.info("No channels configured for backfill; skipping")
            return

        now = datetime.now(tz=timezone.utc)
        oldest = int((now - timedelta(days=7)).timestamp())

        for channel in channels:
            self._process_channel(channel, oldest)

    def _get_target_channels(self) -> list[str]:
        """Return the list of channel IDs to backfill."""
        if self.config.slack_channel_ids:
            return self.config.slack_channel_ids

        # If no restriction, discover public/private channels the bot is in
        try:
            resp = self.client.users_conversations(
                types="public_channel,private_channel",
                exclude_archived=True,
                limit=200,
            )
            return [c["id"] for c in resp.get("channels", [])]
        except SlackApiError as e:
            logger.warning(f"Could not list channels for backfill: {e}")
            return []

    def _process_channel(self, channel: str, oldest: int) -> None:
        """Fetch history and process messages with unhandled links."""
        logger.info(f"Backfilling channel {channel} since epoch {oldest}")

        cursor: str | None = None
        processed_msgs = 0
        added_tracks = 0

        while True:
            try:
                resp = self.client.conversations_history(
                    channel=channel,
                    oldest=str(oldest),
                    limit=200,
                    cursor=cursor,
                )
            except SlackApiError as e:
                logger.error(f"Failed to fetch history for {channel}: {e}")
                break

            messages = resp.get("messages", [])
            for msg in messages:
                if self._should_skip_message(msg):
                    continue

                links = extract_music_links(msg.get("text", ""))
                if not links:
                    continue

                if self._has_bot_tick(msg, channel):
                    continue

                processed_msgs += 1
                for link in links:
                    success = self.message_handler.process_link_standalone(
                        link, channel, msg["ts"], self.client
                    )
                    if success:
                        added_tracks += 1

            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

            # Respect Slack rate limits
            time.sleep(0.5)

        logger.info(
            f"Backfill complete for {channel}: "
            f"{processed_msgs} messages processed, {added_tracks} track(s) added"
        )

    def _should_skip_message(self, msg: dict) -> bool:
        """Return True if the message should be ignored."""
        if msg.get("bot_id") or msg.get("subtype") == "bot_message":
            return True
        if msg.get("subtype") in (
            "channel_join",
            "channel_leave",
            "thread_broadcast",
            "channel_topic",
            "channel_purpose",
        ):
            return True
        return False

    def _has_bot_tick(self, msg: dict, channel: str) -> bool:
        """Check whether the bot has already reacted with :white_check_mark:."""
        try:
            resp = self.client.reactions_get(
                channel=channel,
                timestamp=msg["ts"],
                full=True,
            )
        except SlackApiError as e:
            logger.warning(f"Could not get reactions for {msg['ts']}: {e}")
            return False  # assume no tick to be safe

        message = resp.get("message", {})
        for reaction in message.get("reactions", []):
            if reaction.get("name") == "white_check_mark":
                users = reaction.get("users", [])
                if not users:
                    continue
                if self.bot_user_id in users:
                    return True
        return False

    @property
    def bot_user_id(self) -> str:
        """Lazy-load and cache the bot's own user ID."""
        if self._bot_user_id is None:
            try:
                auth = self.client.auth_test()
                uid = auth.get("user_id")
                self._bot_user_id = uid if uid is not None else ""
            except SlackApiError as e:
                logger.error(f"Could not determine bot user ID: {e}")
                self._bot_user_id = ""
        return self._bot_user_id
