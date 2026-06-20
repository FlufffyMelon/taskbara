from dataclasses import dataclass
import os
from dotenv import load_dotenv, set_key


@dataclass
class Config:
    bot_token: str
    db_path: str
    log_file: str
    log_level: str


def _prompt_for_token(env_file: str) -> str:
    """Ask the user to paste the bot token and persist it to env_file."""
    print("BOT_TOKEN не найден. Получи токен у @BotFather и вставь его сюда.")
    while True:
        token = input("BOT_TOKEN: ").strip()
        if token:
            break
        print("Токен не может быть пустым, попробуй ещё раз.")
    set_key(env_file, "BOT_TOKEN", token)
    print(f"Токен сохранён в {env_file}.")
    return token


def load_config(env_file: str = ".env") -> Config:
    load_dotenv(env_file)

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        bot_token = _prompt_for_token(env_file)

    return Config(
        bot_token=bot_token,
        db_path=os.getenv("DB_PATH", "taskbara.db"),
        log_file=os.getenv("LOG_FILE", "taskbara.log"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
