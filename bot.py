import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
from handlers import router
from database import init_db
from middlewares import ChatLoggingMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def main():
    if not config.BOT_TOKEN:
        logger.error("ОШИБКА: BOT_TOKEN не задан! Укажите токен в файле .env")
        sys.exit(1)

    # Инициализация базы данных
    await init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Регистрация middleware для логирования истории сообщений пользователя
    dp.message.middleware(ChatLoggingMiddleware())
    dp.callback_query.middleware(ChatLoggingMiddleware())

    dp.include_router(router)

    logger.info("Бот AntiScammer запускается...")
    
    # Сбрасываем старые апдейты перед запуском
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
