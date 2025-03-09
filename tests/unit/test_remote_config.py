from usdb_syncer import remote_config


def test_discord_webhook_url() -> None:
    """Tests local config, not the one on GitHub main."""
    assert remote_config.discord_webhook_url() is not None
