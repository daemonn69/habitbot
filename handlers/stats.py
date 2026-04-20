from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import (
    get_habits, get_habit_completion_today, get_completions_for_period,
    get_streak, get_today_completions, update_reminder_time, get_user
)
from keyboards.inline import (
    stats_period_keyboard, back_to_menu_keyboard,
    main_menu_keyboard, cancel_keyboard
)
from utils.formatters import (
    format_habit_status, format_streak, format_weekly_stats, progress_bar
)

router = Router()


class ReminderStates(StatesGroup):
    waiting_for_time = State()


# ============ Меню статистики ============

@router.callback_query(F.data == "stats")
async def stats_menu(callback: CallbackQuery):
    """Меню выбора периода статистики."""
    await callback.message.edit_text(
        "📊 <b>Статистика</b>\n\n"
        "Выбери период:",
        reply_markup=stats_period_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============ Статистика за сегодня ============

@router.callback_query(F.data == "stats_today")
async def stats_today(callback: CallbackQuery):
    """Статистика за сегодня."""
    habits = await get_habits(callback.from_user.id)

    if not habits:
        await callback.message.edit_text(
            "📊 У тебя пока нет привычек.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = "📅 <b>Сегодня</b>\n\n"
    completed_count = 0
    total_count = len(habits)

    for h in habits:
        completion = await get_habit_completion_today(h["id"], callback.from_user.id)
        current = completion["value"] if completion else 0

        status = format_habit_status(
            h["name"], current, h["target_value"],
            h["unit"], h["habit_type"]
        )
        text += f"{status}\n\n"

        # Считаем выполненные
        if h["habit_type"] == "binary" and current >= 1:
            completed_count += 1
        elif h["habit_type"] == "quantity" and current >= h["target_value"]:
            completed_count += 1

    # Общий прогресс дня
    day_bar = progress_bar(completed_count, total_count)
    text += f"━━━━━━━━━━━━━━━\n"
    text += f"📈 Общий прогресс: {completed_count}/{total_count}\n{day_bar}"

    if completed_count == total_count and total_count > 0:
        text += "\n\n🎉 <b>ВСЕ ПРИВЫЧКИ ВЫПОЛНЕНЫ!</b> Ты огонь! 🔥"

    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============ Статистика за неделю ============

@router.callback_query(F.data == "stats_week")
async def stats_week(callback: CallbackQuery):
    """Недельная статистика."""
    habits = await get_habits(callback.from_user.id)

    if not habits:
        await callback.message.edit_text(
            "📊 У тебя пока нет привычек.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = "📊 <b>Статистика за 7 дней</b>\n\n"

    for h in habits:
        completions = await get_completions_for_period(h["id"], callback.from_user.id, 7)
        streak = await get_streak(h["id"], callback.from_user.id)

        stats = format_weekly_stats(
            h["name"], completions, h["target_value"],
            h["unit"], h["habit_type"], streak
        )
        text += f"{stats}\n\n{'━' * 20}\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============ Статистика за месяц ============

@router.callback_query(F.data == "stats_month")
async def stats_month(callback: CallbackQuery):
    """Месячная статистика."""
    habits = await get_habits(callback.from_user.id)

    if not habits:
        await callback.message.edit_text(
            "📊 У тебя пока нет привычек.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = "📈 <b>Статистика за 30 дней</b>\n\n"

    for h in habits:
        completions = await get_completions_for_period(h["id"], callback.from_user.id, 30)
        streak = await get_streak(h["id"], callback.from_user.id)

        # Считаем дни с выполнением
        if h["habit_type"] == "binary":
            done_days = sum(1 for c in completions if c.get("value", 0) >= 1)
            text += f"✅ <b>{h['name']}</b>\n"
            text += f"{format_streak(streak)}\n"
            text += f"Выполнено: {done_days}/30 дней\n"
            text += f"{progress_bar(done_days, 30)}\n\n"
        else:
            total = sum(c.get("value", 0) for c in completions)
            done_days = sum(1 for c in completions if c.get("value", 0) >= h["target_value"])
            monthly_target = h["target_value"] * 30
            unit_text = f" {h['unit']}" if h["unit"] else ""

            total_display = int(total) if total == int(total) else round(total, 1)
            monthly_display = int(monthly_target) if monthly_target == int(monthly_target) else monthly_target

            text += f"🔢 <b>{h['name']}</b>\n"
            text += f"{format_streak(streak)}\n"
            text += f"Всего: {total_display}/{monthly_display}{unit_text}\n"
            text += f"{progress_bar(total, monthly_target)}\n"
            text += f"Дней с целью: {done_days}/30\n\n"

        text += f"{'━' * 20}\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============ Настройка напоминаний ============

@router.callback_query(F.data == "set_reminder")
async def set_reminder(callback: CallbackQuery, state: FSMContext):
    """Настройка времени напоминания."""
    user = await get_user(callback.from_user.id)
    current_time = user["reminder_time"] if user else "09:00"

    await callback.message.edit_text(
        f"⏰ <b>Настройка напоминаний</b>\n\n"
        f"Текущее время: <b>{current_time}</b>\n\n"
        f"Введи новое время в формате <b>ЧЧ:ММ</b>\n"
        f"Например: 08:00, 21:30, 07:15",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(ReminderStates.waiting_for_time)
    await callback.answer()


@router.message(ReminderStates.waiting_for_time)
async def process_reminder_time(message: Message, state: FSMContext):
    """Обработка нового времени напоминания."""
    time_str = message.text.strip()

    # Валидация формата
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            raise ValueError
        hours = int(parts[0])
        minutes = int(parts[1])
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
        time_str = f"{hours:02d}:{minutes:02d}"
    except ValueError:
        await message.answer(
            "❌ Неверный формат! Введи время как <b>ЧЧ:ММ</b>\n"
            "Например: 09:00, 21:30",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        return

    await update_reminder_time(message.from_user.id, time_str)
    await state.clear()

    await message.answer(
        f"✅ Время напоминания установлено: <b>{time_str}</b>\n\n"
        f"Буду напоминать тебе каждый день в это время! 🔔",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
