from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import add_habit, get_habits, get_habit_by_id, delete_habit
from keyboards.inline import (
    habit_type_keyboard, habits_list_keyboard,
    confirm_delete_keyboard, back_to_menu_keyboard,
    main_menu_keyboard, cancel_keyboard
)
from utils.formatters import format_habit_type_display

router = Router()


# ============ FSM States ============

class AddHabitStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_type = State()
    waiting_for_target = State()
    waiting_for_unit = State()


# ============ Добавление привычки ============

@router.callback_query(F.data == "add_habit")
async def start_add_habit(callback: CallbackQuery, state: FSMContext):
    """Начало добавления привычки."""
    await callback.message.edit_text(
        "➕ <b>Новая привычка</b>\n\n"
        "Напиши <b>название</b> привычки.\n\n"
        "Примеры:\n"
        "• Отжимания\n"
        "• Выпить воду\n"
        "• Почитать книгу\n"
        "• Пробежка",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AddHabitStates.waiting_for_name)
    await callback.answer()


@router.message(AddHabitStates.waiting_for_name)
async def process_habit_name(message: Message, state: FSMContext):
    """Получение названия привычки."""
    name = message.text.strip()
    if len(name) > 50:
        await message.answer(
            "❌ Слишком длинное название! Максимум 50 символов.",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    await state.update_data(name=name)
    await message.answer(
        f"📝 Привычка: <b>{name}</b>\n\n"
        "Выбери <b>тип</b> привычки:",
        reply_markup=habit_type_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddHabitStates.waiting_for_type)


@router.callback_query(AddHabitStates.waiting_for_type, F.data.startswith("type_"))
async def process_habit_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа привычки."""
    habit_type = callback.data.replace("type_", "")
    await state.update_data(habit_type=habit_type)

    if habit_type == "binary":
        # Для бинарных — сразу сохраняем
        data = await state.get_data()
        habit_id = await add_habit(
            user_id=callback.from_user.id,
            name=data["name"],
            habit_type="binary",
            target_value=1,
            unit=""
        )
        await state.clear()
        await callback.message.edit_text(
            f"✅ Привычка <b>«{data['name']}»</b> добавлена!\n\n"
            f"Тип: ✅ Да/Нет\n"
            f"Просто отмечай выполнение каждый день 💪",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        # Для количественных — спрашиваем цель
        await callback.message.edit_text(
            "🎯 Введи <b>цель на день</b> (число).\n\n"
            "Например:\n"
            "• 50 (отжиманий)\n"
            "• 2 (литра воды)\n"
            "• 10 (страниц книги)",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(AddHabitStates.waiting_for_target)

    await callback.answer()


@router.message(AddHabitStates.waiting_for_target)
async def process_habit_target(message: Message, state: FSMContext):
    """Получение целевого значения."""
    try:
        target = float(message.text.strip().replace(",", "."))
        if target <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Введи <b>положительное число</b>! Например: 50",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(target_value=target)
    await message.answer(
        "📏 Введи <b>единицу измерения</b> (или отправь <b>-</b> чтобы пропустить).\n\n"
        "Примеры: шт, раз, л, км, мин, страниц",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AddHabitStates.waiting_for_unit)


@router.message(AddHabitStates.waiting_for_unit)
async def process_habit_unit(message: Message, state: FSMContext):
    """Получение единицы измерения и сохранение привычки."""
    unit = message.text.strip()
    if unit == "-":
        unit = ""

    data = await state.get_data()
    habit_id = await add_habit(
        user_id=message.from_user.id,
        name=data["name"],
        habit_type=data["habit_type"],
        target_value=data["target_value"],
        unit=unit
    )
    await state.clear()

    target_display = int(data["target_value"]) if data["target_value"] == int(data["target_value"]) else data["target_value"]
    unit_text = f" {unit}" if unit else ""

    await message.answer(
        f"✅ Привычка <b>«{data['name']}»</b> добавлена!\n\n"
        f"🎯 Цель: {target_display}{unit_text} в день\n"
        f"Тип: {format_habit_type_display(data['habit_type'])}\n\n"
        f"Теперь отмечай прогресс каждый день! 💪",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


# ============ Список привычек ============

@router.callback_query(F.data == "my_habits")
async def show_habits(callback: CallbackQuery):
    """Показать список привычек."""
    habits = await get_habits(callback.from_user.id)

    if not habits:
        await callback.message.edit_text(
            "📋 У тебя пока нет привычек.\n\n"
            "Нажми <b>➕ Добавить привычку</b> чтобы начать!",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = "📋 <b>Твои привычки:</b>\n\n"
    for i, h in enumerate(habits, 1):
        emoji = "🔢" if h["habit_type"] == "quantity" else "✅"
        target_display = ""
        if h["habit_type"] == "quantity":
            target = int(h["target_value"]) if h["target_value"] == int(h["target_value"]) else h["target_value"]
            unit_text = f" {h['unit']}" if h["unit"] else ""
            target_display = f" — цель: {target}{unit_text}/день"
        text += f"{i}. {emoji} <b>{h['name']}</b>{target_display}\n"

    text += "\n<i>Нажми на привычку для управления:</i>"

    await callback.message.edit_text(
        text,
        reply_markup=habits_list_keyboard(habits, action="manage"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("habit_manage_"))
async def manage_habit(callback: CallbackQuery):
    """Управление конкретной привычкой."""
    habit_id = int(callback.data.replace("habit_manage_", ""))
    habit = await get_habit_by_id(habit_id)

    if not habit:
        await callback.answer("❌ Привычка не найдена", show_alert=True)
        return

    target_display = ""
    if habit["habit_type"] == "quantity":
        target = int(habit["target_value"]) if habit["target_value"] == int(habit["target_value"]) else habit["target_value"]
        unit_text = f" {habit['unit']}" if habit["unit"] else ""
        target_display = f"\n🎯 Цель: {target}{unit_text}/день"

    text = (
        f"⚙️ <b>{habit['name']}</b>\n\n"
        f"Тип: {format_habit_type_display(habit['habit_type'])}"
        f"{target_display}\n"
        f"📅 Создана: {habit['created_at'][:10]}\n\n"
        f"Удалить привычку?"
    )

    await callback.message.edit_text(
        text,
        reply_markup=confirm_delete_keyboard(habit_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete(callback: CallbackQuery):
    """Подтверждение удаления привычки."""
    habit_id = int(callback.data.replace("confirm_delete_", ""))
    habit = await get_habit_by_id(habit_id)

    if habit:
        await delete_habit(habit_id)
        await callback.message.edit_text(
            f"🗑 Привычка <b>«{habit['name']}»</b> удалена.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Привычка не найдена", show_alert=True)

    await callback.answer()


# ============ Отмена ============

@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.\n\n🏠 <b>Главное меню</b>",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
