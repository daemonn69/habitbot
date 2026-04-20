from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import (
    get_habits, get_habit_by_id, log_completion,
    get_habit_completion_today, get_streak
)
from keyboards.inline import (
    habits_list_keyboard, binary_log_keyboard,
    back_to_menu_keyboard, main_menu_keyboard,
    cancel_keyboard
)
from utils.formatters import format_habit_status, format_streak, progress_bar

router = Router()


class LogHabitStates(StatesGroup):
    waiting_for_value = State()


# ============ Выбор привычки для логирования ============

@router.callback_query(F.data == "log_habit")
async def choose_habit_to_log(callback: CallbackQuery):
    """Выбор привычки для отметки."""
    habits = await get_habits(callback.from_user.id)

    if not habits:
        await callback.message.edit_text(
            "📋 У тебя пока нет привычек.\n\n"
            "Сначала добавь привычку!",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # Показываем статус каждой привычки
    text = "✏️ <b>Отметить привычку</b>\n\n"
    for h in habits:
        completion = await get_habit_completion_today(h["id"], callback.from_user.id)
        current = completion["value"] if completion else 0

        status = format_habit_status(
            h["name"], current, h["target_value"],
            h["unit"], h["habit_type"]
        )
        text += f"{status}\n\n"

    text += "<i>Выбери привычку для отметки:</i>"

    await callback.message.edit_text(
        text,
        reply_markup=habits_list_keyboard(habits, action="log"),
        parse_mode="HTML"
    )
    await callback.answer()


# ============ Логирование ============

@router.callback_query(F.data.startswith("habit_log_"))
async def start_log_habit(callback: CallbackQuery, state: FSMContext):
    """Начало логирования привычки."""
    habit_id = int(callback.data.replace("habit_log_", ""))
    habit = await get_habit_by_id(habit_id)

    if not habit:
        await callback.answer("❌ Привычка не найдена", show_alert=True)
        return

    if habit["habit_type"] == "binary":
        # Для бинарных — показываем кнопку
        completion = await get_habit_completion_today(habit_id, callback.from_user.id)
        if completion and completion["value"] >= 1:
            await callback.message.edit_text(
                f"✅ <b>{habit['name']}</b> — уже выполнено сегодня! 🎉",
                reply_markup=back_to_menu_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"✅ <b>{habit['name']}</b>\n\n"
                f"Выполнил сегодня?",
                reply_markup=binary_log_keyboard(habit_id),
                parse_mode="HTML"
            )
    else:
        # Для количественных — спрашиваем значение
        completion = await get_habit_completion_today(habit_id, callback.from_user.id)
        current = completion["value"] if completion else 0
        target = habit["target_value"]
        unit_text = f" {habit['unit']}" if habit["unit"] else ""

        current_display = int(current) if current == int(current) else current
        target_display = int(target) if target == int(target) else target

        bar = progress_bar(current, target)

        await state.update_data(habit_id=habit_id)
        await callback.message.edit_text(
            f"📝 <b>{habit['name']}</b>\n\n"
            f"Сейчас: {current_display}/{target_display}{unit_text}\n"
            f"{bar}\n\n"
            f"Введи <b>число</b> — сколько сделал:",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(LogHabitStates.waiting_for_value)

    await callback.answer()


@router.message(LogHabitStates.waiting_for_value)
async def process_log_value(message: Message, state: FSMContext):
    """Обработка введённого значения."""
    try:
        value = float(message.text.strip().replace(",", "."))
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Введи <b>положительное число</b>!",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        return

    data = await state.get_data()
    habit_id = data["habit_id"]
    habit = await get_habit_by_id(habit_id)

    if not habit:
        await state.clear()
        await message.answer("❌ Привычка не найдена.", reply_markup=main_menu_keyboard())
        return

    # Логируем
    await log_completion(habit_id, message.from_user.id, value)
    await state.clear()

    # Получаем обновлённый прогресс
    completion = await get_habit_completion_today(habit_id, message.from_user.id)
    current = completion["value"] if completion else value
    target = habit["target_value"]
    unit_text = f" {habit['unit']}" if habit["unit"] else ""

    current_display = int(current) if current == int(current) else current
    target_display = int(target) if target == int(target) else target

    bar = progress_bar(current, target)
    streak = await get_streak(habit_id, message.from_user.id)

    # Мотивационное сообщение
    if current >= target:
        motivation = "🎉 <b>ЦЕЛЬ ДОСТИГНУТА!</b> Красава! 💪"
    elif current >= target * 0.75:
        motivation = "🔥 Почти! Ещё чуть-чуть!"
    elif current >= target * 0.5:
        motivation = "💪 Больше половины! Давай!"
    else:
        motivation = "🚀 Хорошее начало! Продолжай!"

    await message.answer(
        f"✏️ <b>{habit['name']}</b> — записано!\n\n"
        f"📊 Прогресс: {current_display}/{target_display}{unit_text}\n"
        f"{bar}\n\n"
        f"{format_streak(streak)}\n\n"
        f"{motivation}",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


# ============ Бинарное логирование ============

@router.callback_query(F.data.startswith("binary_done_"))
async def binary_done(callback: CallbackQuery):
    """Отметка бинарной привычки как выполненной."""
    habit_id = int(callback.data.replace("binary_done_", ""))
    habit = await get_habit_by_id(habit_id)

    if not habit:
        await callback.answer("❌ Привычка не найдена", show_alert=True)
        return

    # Проверяем не отмечена ли уже
    completion = await get_habit_completion_today(habit_id, callback.from_user.id)
    if completion and completion["value"] >= 1:
        await callback.answer("✅ Уже отмечено сегодня!", show_alert=True)
        return

    await log_completion(habit_id, callback.from_user.id, 1)
    streak = await get_streak(habit_id, callback.from_user.id)

    await callback.message.edit_text(
        f"✅ <b>{habit['name']}</b> — выполнено! 🎉\n\n"
        f"{format_streak(streak)}\n\n"
        f"Так держать! 💪",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("✅ Отмечено!")
