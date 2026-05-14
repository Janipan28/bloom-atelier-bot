from functools import lru_cache
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    bot_username: str
    channel_id: str | int
    admin_chat_id: int
    staff_channel_id: int = 0
    admin_ids: str = ""
    database_url: str = "sqlite+aiosqlite:///./flower_bot.sqlite3"
    mini_app_url: str = ""
    admin_panel_url: str = ""
    timezone: str = "Europe/Moscow"
    default_order_button_text: str = "Заказать"

    # Robokassa
    robokassa_merchant_login: str = ""
    robokassa_pass1: str = ""
    robokassa_pass2: str = ""
    robokassa_is_test: int = 1

    # Loyalty
    loyalty_cashback_percent: int = 5


    @property
    def admin_id_set(self) -> set[int]:
        result = set()
        for raw in self.admin_ids.split(","):
            raw = raw.strip()
            if raw:
                result.add(int(raw))
        return result



@lru_cache
def get_settings() -> Settings:
    return Settings()
