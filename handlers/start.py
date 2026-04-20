from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from database.db import add_user, get_user
from keyboards.inline import main_menu_keyboard

router = Router()

WELCOME_TEXT = """
🏋️ <b>Привет, {name}!</b>

Я — твой <b>трекер привычек</b>! 💪

Я помогу тебе:
• ➕ Добавлять ежедневные цели
• ✏️ Отмечать прогресс
• 📊 Смотреть статистику
• 🔔 Напоминать о привычках
• 🔥 Считать стрики

<b>Начнём?</b> Жми кнопки ниже 👇
"""


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start."""
    user = message.from_user
    await add_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "Друг"
    )

    await message.answer(
        WELCOME_TEXT.format(name=user.first_name or "Друг"),
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.message.edit_text(
        f"🏠 <b>Главное меню</b>\n\nВыбери действие:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
