"""Slack event handlers for processing music links."""

import logging
import re

from slack_bolt import App

from .config import Config
from .extractors import MusicLink, TrackInfo, extract_music_links, get_youtube_track_info
from .spotify import SpotifyClient

logger = logging.getLogger(__name__)

# Pattern to match "add: Artist - Song" (supports -, –, and — as separators)
ADD_COMMAND_PATTERN = re.compile(
    r"add:\s*(.+?)\s*[-–—]\s*(.+)",
    re.IGNORECASE,
)


class MessageHandler:
    """Handles Slack messages containing music links."""

    def __init__(self, config: Config, spotify: SpotifyClient):
        """Initialize the handler.

        Args:
            config: Application configuration.
            spotify: Spotify client for track operations.
        """
        self.config = config
        self.spotify = spotify

    def handle_message(self, event: dict, client, say) -> None:
        """Process a Slack message event.

        Args:
            event: Slack message event dict.
            client: Slack WebClient for API calls.
            say: Function to send messages.
        """
        # Ignore bot messages to prevent loops
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return

        # Check channel filter if configured
        channel = event.get("channel")
        if self.config.slack_channel_ids and channel not in self.config.slack_channel_ids:
            return

        text = event.get("text", "")
        links = extract_music_links(text)

        if not links:
            return

        logger.info(f"Found {len(links)} music link(s) in message")

        for link in links:
            self._process_link(link, event, client)

    def _process_link(self, link: MusicLink, event: dict, client) -> None:
        """Process a single music link.

        Args:
            link: Parsed music link.
            event: Original Slack event.
            client: Slack WebClient.
        """
        channel = event["channel"]
        ts = event["ts"]

        try:
            track, track_info = self._resolve_track(link)

            if not track:
                logger.warning(f"Could not find Spotify track for {link.url}")
                client.reactions_add(channel=channel, timestamp=ts, name="question")
                message = f":question: Could not find Spotify track for: {link.url}"
                if track_info:
                    message += f"\nyt-dlp metadata — Title: {track_info.title}, Artist: {track_info.artist}"
                self._send_debug_message(client, channel, ts, message)
                return

            track_id = track["id"]
            display_name = self.spotify.get_track_display_name(track)

            if self.spotify.add_to_playlist(track_id):
                logger.info(f"Added to playlist: {display_name}")
                client.reactions_add(channel=channel, timestamp=ts, name="white_check_mark")
            else:
                logger.error(f"Failed to add to playlist: {display_name}")
                client.reactions_add(channel=channel, timestamp=ts, name="x")
                self._send_debug_message(
                    client, channel, ts,
                    f":x: Failed to add to playlist: {display_name}"
                )

        except Exception as e:
            logger.error(f"Error processing link {link.url}: {e}")
            try:
                client.reactions_add(channel=channel, timestamp=ts, name="x")
                self._send_debug_message(
                    client, channel, ts,
                    f":x: Error processing link {link.url}: {e}"
                )
            except Exception:
                pass  # Best effort reaction

    def _send_debug_message(self, client, channel: str, thread_ts: str, message: str) -> None:
        """Send a debug message to the channel as a thread reply.

        Args:
            client: Slack WebClient.
            channel: Channel ID.
            thread_ts: Parent message timestamp to reply to.
            message: Debug message to send.
        """
        if not self.config.debug_messages:
            return

        try:
            client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=message,
            )
        except Exception as e:
            logger.warning(f"Failed to send debug message: {e}")

    def _resolve_track(self, link: MusicLink) -> tuple[dict | None, "TrackInfo | None"]:
        """Resolve a music link to a Spotify track.

        Args:
            link: Parsed music link.

        Returns:
            Tuple of (Spotify track dict, TrackInfo) — either may be None.
        """
        if link.source == "spotify":
            return self.spotify.get_track(link.id), None

        elif link.source == "youtube":
            track_info = get_youtube_track_info(link.url)

            if not track_info:
                return None, None

            return self.spotify.search_track(track_info.title, track_info.artist), track_info

        return None, None


class MentionHandler:
    """Handles @groovebot mentions with commands."""

    def __init__(self, config: Config, spotify: SpotifyClient):
        self.config = config
        self.spotify = spotify

    def handle_mention(self, event: dict, client, say) -> None:
        """Process an app_mention event.

        Args:
            event: Slack app_mention event dict.
            client: Slack WebClient for API calls.
            say: Function to send messages.
        """
        text = event.get("text", "")
        channel = event.get("channel")
        ts = event.get("ts")

        # Strip the bot mention (<@BOTID>) to get the command text
        command_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

        if command_text.lower().startswith("add:"):
            self._handle_add(command_text, channel, ts, client, say)
        elif command_text.lower() in ("help", ""):
            self._handle_help(channel, ts, say)
        else:
            say(
                text=f":question: Unknown command. Try `@groovebot help` for usage info.",
                thread_ts=ts,
            )

    def _handle_add(self, command_text: str, channel: str, ts: str, client, say) -> None:
        """Handle the 'add: Artist - Song' command.

        Args:
            command_text: The command text after the bot mention.
            channel: Channel ID.
            ts: Message timestamp.
            client: Slack WebClient.
            say: Function to send messages.
        """
        match = ADD_COMMAND_PATTERN.match(command_text)
        if not match:
            say(
                text=(
                    ":warning: Couldn't parse that. Use the format:\n"
                    "`@groovebot add: Artist - Song Name`"
                ),
                thread_ts=ts,
            )
            return

        artist = match.group(1).strip()
        song = match.group(2).strip()

        logger.info(f"Add command: artist='{artist}', song='{song}'")

        track = self.spotify.search_track(song, artist)
        if not track:
            logger.warning(f"Could not find Spotify track for '{artist} - {song}'")
            client.reactions_add(channel=channel, timestamp=ts, name="question")
            say(
                text=f":question: Couldn't find a Spotify track for: *{artist} - {song}*",
                thread_ts=ts,
            )
            return

        track_id = track["id"]
        display_name = self.spotify.get_track_display_name(track)

        if self.spotify.add_to_playlist(track_id):
            logger.info(f"Added to playlist via command: {display_name}")
            client.reactions_add(channel=channel, timestamp=ts, name="white_check_mark")
        else:
            logger.error(f"Failed to add to playlist: {display_name}")
            client.reactions_add(channel=channel, timestamp=ts, name="x")
            say(
                text=f":x: Failed to add to playlist: *{display_name}*",
                thread_ts=ts,
            )

    def _handle_help(self, channel: str, ts: str, say) -> None:
        """Send the help message.

        Args:
            channel: Channel ID.
            ts: Message timestamp.
            say: Function to send messages.
        """
        playlist_url = f"https://open.spotify.com/playlist/{self.config.spotify_playlist_id}"
        help_text = (
            ":musical_note: *Groovebot Help*\n\n"
            "*Automatic link detection:*\n"
            "Post a YouTube or Spotify link in the channel and I'll "
            "automatically add the track to the shared Spotify playlist.\n\n"
            "*Manual add:*\n"
            "`@groovebot add: Artist - Song Name`\n"
            "Search Spotify for a track by artist and song name and add it "
            "to the playlist.\n\n"
            "*Reactions:*\n"
            "\u2022 :white_check_mark: — Track was added to the playlist\n"
            "\u2022 :question: — Couldn't find a matching track on Spotify\n"
            "\u2022 :x: — Something went wrong adding the track\n\n"
            f":spotify: *Playlist Link:* {playlist_url}"
        )
        say(text=help_text, thread_ts=ts)


def register_handlers(app: App, config: Config, spotify: SpotifyClient) -> None:
    """Register event handlers with the Slack app.

    Args:
        app: Slack Bolt application.
        config: Application configuration.
        spotify: Spotify client.
    """
    message_handler = MessageHandler(config, spotify)
    mention_handler = MentionHandler(config, spotify)

    @app.event("message")
    def handle_message_event(event, client, say):
        message_handler.handle_message(event, client, say)

    @app.event("app_mention")
    def handle_app_mention_event(event, client, say):
        mention_handler.handle_mention(event, client, say)

    logger.info("Message and mention handlers registered")
