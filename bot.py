import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from handlers import start, habits, logging as log_handler, stats
from scheduler.reminders import setup_scheduler, stop_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def main():
    """Точка входа."""
    # Проверка токена
    if not BOT_TOKEN or BOT_TOKEN == "СЮДА_ВСТАВЬ_ТОКЕН_ОТ_BOTFATHER":
        logger.error(
            "❌ Токен бота не установлен!\n"
            "Открой файл .env и вставь токен от @BotFather:\n"
            "BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
        )
        return

    # Инициализация
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(habits.router)
    dp.include_router(log_handler.router)
    dp.include_router(stats.router)

    # Инициализация БД
    await init_db()
    logger.info("✅ База данных инициализирована")

    # Запуск планировщика напоминаний
    setup_scheduler(bot)

    # Запуск бота
    logger.info("🚀 Бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        stop_scheduler()
        await bot.session.close()
        logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен (Ctrl+C)")
