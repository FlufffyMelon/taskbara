import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent

from .config import load_config
from .logging_setup import setup_logging
from .db import init_db
from .handlers import router

logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()
    setup_logging(config.log_file, config.log_level)

    await init_db(config.db_path)

    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    # Inject db_path into handlers via dispatcher workflow data
    dp["db_path"] = config.db_path

    dp.include_router(router)

    @dp.errors()
    async def error_handler(event: ErrorEvent) -> None:
        logger.error("Unhandled error: %s", event.exception, exc_info=event.exception)

    logger.info("Starting taskbara bot")
    await dp.start_polling(bot)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
