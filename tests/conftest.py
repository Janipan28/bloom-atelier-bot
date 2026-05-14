import pytest
from unittest.mock import MagicMock, AsyncMock
import os

# Предотвращаем загрузку реальных настроек
os.environ["BOT_TOKEN"] = "fake_token"
os.environ["BOT_USERNAME"] = "fake_bot"
os.environ["CHANNEL_ID"] = "123"
os.environ["ADMIN_CHAT_ID"] = "456"

@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    mock = MagicMock()
    mock.bot_token = "fake_token"
    mock.bot_username = "fake_bot"
    mock.channel_id = 123
    mock.admin_chat_id = 456
    mock.admin_id_set = {456}
    
    import bot.config
    monkeypatch.setattr(bot.config, "get_settings", lambda: mock)
    return mock

@pytest.fixture
def mock_db_session(monkeypatch):
    session = AsyncMock()
    # Мокаем асинхронный контекстный менеджер
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__.return_value = session
    
    import bot.db
    monkeypatch.setattr(bot.db, "async_session", lambda: mock_session_cm)
    return session
