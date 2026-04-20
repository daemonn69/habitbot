import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database.db import get_all_users, get_uncompleted_habits
from keyboards.inline import reminder_habits_keyboard

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_bot = None


def setup_scheduler(bot):
    """Инициализация планировщика с экземпляром бота."""
    global _bot
    _bot = bot

    # Проверяем каждую минуту, нужно ли кому отправить напоминание
    scheduler.add_job(
        check_and_send_reminders,
        CronTrigger(minute="*"),  # каждую минуту
        id="reminder_check",
        replace_existing=True
    )
    scheduler.start()
    logger.info("📅 Планировщик напоминаний запущен")


async def check_and_send_reminders():
    """Проверка и отправка напоминаний."""
    if _bot is None:
        return

    now = datetime.now()
    current_time = now.strftime("%H:%M")

    try:
        users = await get_all_users()

        for user in users:
            if user["reminder_time"] == current_time:
                await send_reminder(user["user_id"])

    except Exception as e:
        logger.error(f"Ошибка при отправке напоминаний: {e}")


async def send_reminder(user_id: int):
    """Отправка напоминания конкретному пользователю."""
    if _bot is None:
        return

    try:
        uncompleted = await get_uncompleted_habits(user_id)

        if not uncompleted:
            # Все привычки выполнены — поздравляем!
            try:
                await _bot.send_message(
                    user_id,
                    "🎉 <b>Все привычки на сегодня выполнены!</b>\n\n"
                    "Ты молодец! Так держать! 💪🔥",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            return

        # Формируем список невыполненных
        text = "🔔 <b>Напоминание!</b>\n\n"
        text += "Ещё не отмечено сегодня:\n\n"

        for h in uncompleted:
            emoji = "🔢" if h["habit_type"] == "quantity" else "⬜"
            target_text = ""
            if h["habit_type"] == "quantity":
                target = int(h["target_value"]) if h["target_value"] == int(h["target_value"]) else h["target_value"]
                unit_text = f" {h['unit']}" if h["unit"] else ""
                target_text = f" (цель: {target}{unit_text})"
            text += f"  {emoji} {h['name']}{target_text}\n"

        text += "\n💪 Давай, ты можешь!"

        try:
            await _bot.send_message(
                user_id,
                text,
                reply_markup=reminder_habits_keyboard(uncompleted),
                parse_mode="HTML"
            )
            logger.info(f"📨 Напоминание отправлено юзеру {user_id}")
        except Exception as e:
            logger.warning(f"Не удалось отправить напоминание юзеру {user_id}: {e}")

    except Exception as e:
        logger.error(f"Ошибка в send_reminder для {user_id}: {e}")


def stop_scheduler():
    """Остановка планировщика."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("📅 Планировщик остановлен")
