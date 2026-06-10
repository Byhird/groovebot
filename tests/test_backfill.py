"""Tests for backfill module."""

from unittest.mock import MagicMock, patch

import pytest

from groovebot.backfill import BackfillRunner
from groovebot.config import Config
from groovebot.extractors import MusicLink
from groovebot.handlers import MessageHandler
from groovebot.spotify import SpotifyClient


@pytest.fixture
def config():
    return Config(
        slack_bot_token="xoxb-test",
        slack_app_token="xapp-test",
        spotify_client_id="cid",
        spotify_client_secret="csec",
        spotify_refresh_token="rtok",
        spotify_playlist_id="plid",
        slack_channel_ids=["C1"],
        debug_messages=False,
        enable_startup_backfill=True,
    )


@pytest.fixture
def mock_spotify():
    return MagicMock(spec=SpotifyClient)


@pytest.fixture
def mock_handler(mock_spotify, config):
    return MagicMock(spec=MessageHandler(config, mock_spotify))


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.auth_test.return_value = {"user_id": "U_BOT"}
    return client


@pytest.fixture
def runner(config, mock_spotify, mock_handler, mock_client):
    return BackfillRunner(config, mock_spotify, mock_handler, mock_client)


class TestBackfillRunner:
    """Tests for the BackfillRunner orchestration."""

    def test_run_uses_configured_channels(self, runner, mock_client):
        mock_client.conversations_history.return_value = {
            "messages": [],
            "has_more": False,
        }
        runner.run()
        mock_client.conversations_history.assert_called_once()
        args, kwargs = mock_client.conversations_history.call_args
        assert kwargs["channel"] == "C1"

    def test_run_skips_messages_with_x_reaction(self, runner, mock_client, mock_handler):
        mock_client.conversations_history.return_value = {
            "messages": [
                {
                    "ts": "123.456",
                    "text": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "user": "U_USER",
                }
            ],
            "has_more": False,
        }
        mock_client.reactions_get.return_value = {
            "message": {
                "reactions": [
                    {
                        "name": "x",
                        "users": ["U_BOT"],
                    }
                ]
            }
        }

        runner.run()
        mock_handler.process_link_standalone.assert_not_called()

    def test_run_skips_messages_with_question_reaction(self, runner, mock_client, mock_handler):
        mock_client.conversations_history.return_value = {
            "messages": [
                {
                    "ts": "123.456",
                    "text": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "user": "U_USER",
                }
            ],
            "has_more": False,
        }
        mock_client.reactions_get.return_value = {
            "message": {
                "reactions": [
                    {
                        "name": "question",
                        "users": ["U_BOT"],
                    }
                ]
            }
        }

        runner.run()
        mock_handler.process_link_standalone.assert_not_called()

    def test_run_skips_messages_with_bot_tick(self, runner, mock_client, mock_handler):
        mock_client.conversations_history.return_value = {
            "messages": [
                {
                    "ts": "123.456",
                    "text": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "user": "U_USER",
                }
            ],
            "has_more": False,
        }
        mock_client.reactions_get.return_value = {
            "message": {
                "reactions": [
                    {
                        "name": "white_check_mark",
                        "users": ["U_BOT"],
                    }
                ]
            }
        }

        runner.run()
        mock_handler.process_link_standalone.assert_not_called()

    def test_run_processes_message_without_tick(self, runner, mock_client, mock_handler):
        mock_client.conversations_history.return_value = {
            "messages": [
                {
                    "ts": "123.456",
                    "text": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "user": "U_USER",
                }
            ],
            "has_more": False,
        }
        mock_client.reactions_get.return_value = {"message": {"reactions": []}}
        mock_handler.process_link_standalone.return_value = True

        runner.run()
        mock_handler.process_link_standalone.assert_called_once()
        args, _ = mock_handler.process_link_standalone.call_args
        assert args[0].source == "youtube"
        assert args[0].id == "dQw4w9WgXcQ"

    def test_run_skips_bot_messages(self, runner, mock_client, mock_handler):
        mock_client.conversations_history.return_value = {
            "messages": [
                {
                    "ts": "123.456",
                    "text": "https://youtu.be/dQw4w9WgXcQ",
                    "bot_id": "B_BOT",
                    "subtype": "bot_message",
                }
            ],
            "has_more": False,
        }
        runner.run()
        mock_handler.process_link_standalone.assert_not_called()

    def test_run_skips_channel_join_messages(self, runner, mock_client, mock_handler):
        mock_client.conversations_history.return_value = {
            "messages": [
                {
                    "ts": "123.456",
                    "text": "<@U_USER> has joined the channel",
                    "subtype": "channel_join",
                    "user": "U_USER",
                }
            ],
            "has_more": False,
        }
        runner.run()
        mock_handler.process_link_standalone.assert_not_called()

    def test_run_paginates_history(self, runner, mock_client, mock_handler):
        mock_client.conversations_history.side_effect = [
            {
                "messages": [
                    {
                        "ts": "100.000",
                        "text": "https://youtu.be/dQw4w9WgXcQ",
                        "user": "U_USER",
                    }
                ],
                "response_metadata": {"next_cursor": "c1"},
            },
            {
                "messages": [
                    {
                        "ts": "200.000",
                        "text": "https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8",
                        "user": "U_USER",
                    }
                ],
                "response_metadata": {},
            },
        ]
        mock_client.reactions_get.return_value = {"message": {"reactions": []}}
        mock_handler.process_link_standalone.return_value = True

        runner.run()
        assert mock_client.conversations_history.call_count == 2
        assert mock_handler.process_link_standalone.call_count == 2

    def test_run_handles_reactions_api_error_gracefully(self, runner, mock_client, mock_handler):
        mock_client.conversations_history.return_value = {
            "messages": [
                {
                    "ts": "123.456",
                    "text": "https://youtu.be/dQw4w9WgXcQ",
                    "user": "U_USER",
                }
            ],
            "has_more": False,
        }
        from slack_sdk.errors import SlackApiError

        mock_client.reactions_get.side_effect = SlackApiError("boom", {"ok": False, "error": "ratelimited"})
        mock_handler.process_link_standalone.return_value = True

        runner.run()
        # Should still attempt to process since we treat error as "no tick"
        mock_handler.process_link_standalone.assert_called_once()

    def test_run_no_channels_when_not_configured(self, mock_spotify, mock_handler, mock_client):
        config_no_channels = Config(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            spotify_client_id="cid",
            spotify_client_secret="csec",
            spotify_refresh_token="rtok",
            spotify_playlist_id="plid",
            slack_channel_ids=None,
            debug_messages=False,
            enable_startup_backfill=True,
        )
        runner = BackfillRunner(config_no_channels, mock_spotify, mock_handler, mock_client)
        mock_client.users_conversations.return_value = {"channels": []}
        runner.run()
        mock_client.users_conversations.assert_called_once()
        mock_client.conversations_history.assert_not_called()

    def test_run_no_messages_with_links(self, runner, mock_client, mock_handler):
        mock_client.conversations_history.return_value = {
            "messages": [
                {"ts": "123.456", "text": "just a normal message", "user": "U_USER"}
            ],
            "has_more": False,
        }
        runner.run()
        mock_handler.process_link_standalone.assert_not_called()

    def test_run_respects_channel_filter(self, mock_spotify, mock_handler, mock_client):
        config_multi = Config(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            spotify_client_id="cid",
            spotify_client_secret="csec",
            spotify_refresh_token="rtok",
            spotify_playlist_id="plid",
            slack_channel_ids=["C_A", "C_B"],
            debug_messages=False,
            enable_startup_backfill=True,
        )
        runner = BackfillRunner(config_multi, mock_spotify, mock_handler, mock_client)
        mock_client.conversations_history.return_value = {
            "messages": [],
            "has_more": False,
        }
        runner.run()
        assert mock_client.conversations_history.call_count == 2
        channels = [c.kwargs["channel"] for c in mock_client.conversations_history.call_args_list]
        assert sorted(channels) == ["C_A", "C_B"]

    def test_is_message_processed_returns_true_when_bot_reacted_with_checkmark(self, runner, mock_client):
        mock_client.reactions_get.return_value = {
            "message": {
                "reactions": [
                    {"name": "white_check_mark", "users": ["U_BOT", "U_OTHER"]}
                ]
            }
        }
        msg = {"ts": "1.0"}
        assert runner._is_message_processed(msg, "C1") is True

    def test_is_message_processed_returns_true_when_bot_reacted_with_x(self, runner, mock_client):
        mock_client.reactions_get.return_value = {
            "message": {
                "reactions": [
                    {"name": "x", "users": ["U_BOT", "U_OTHER"]}
                ]
            }
        }
        msg = {"ts": "1.0"}
        assert runner._is_message_processed(msg, "C1") is True

    def test_is_message_processed_returns_true_when_bot_reacted_with_question(self, runner, mock_client):
        mock_client.reactions_get.return_value = {
            "message": {
                "reactions": [
                    {"name": "question", "users": ["U_BOT", "U_OTHER"]}
                ]
            }
        }
        msg = {"ts": "1.0"}
        assert runner._is_message_processed(msg, "C1") is True

    def test_is_message_processed_returns_false_for_other_reaction(self, runner, mock_client):
        mock_client.reactions_get.return_value = {
            "message": {"reactions": [{"name": "eyes", "users": ["U_BOT"]}]}
        }
        msg = {"ts": "1.0"}
        assert runner._is_message_processed(msg, "C1") is False

    def test_is_message_processed_returns_false_when_other_user_reacted(self, runner, mock_client):
        mock_client.reactions_get.return_value = {
            "message": {
                "reactions": [
                    {"name": "white_check_mark", "users": ["U_OTHER"]}
                ]
            }
        }
        msg = {"ts": "1.0"}
        assert runner._is_message_processed(msg, "C1") is False

    def test_should_skip_message_for_bot(self, runner):
        assert runner._should_skip_message({"bot_id": "B123"}) is True

    def test_should_skip_message_for_channel_join(self, runner):
        assert runner._should_skip_message({"subtype": "channel_join"}) is True

    def test_should_not_skip_normal_message(self, runner):
        assert runner._should_skip_message({"user": "U123", "text": "hello"}) is False
