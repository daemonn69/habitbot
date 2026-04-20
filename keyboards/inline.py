from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить привычку", callback_data="add_habit")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои привычки", callback_data="my_habits"),
        InlineKeyboardButton(text="✏️ Отметить", callback_data="log_habit")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="⏰ Напоминание", callback_data="set_reminder")
    )
    return builder.as_markup()


def habits_list_keyboard(habits: list, action: str = "select") -> InlineKeyboardMarkup:
    """Список привычек в виде кнопок."""
    builder = InlineKeyboardBuilder()
    for habit in habits:
        emoji = "🔢" if habit["habit_type"] == "quantity" else "✅"
        builder.row(
            InlineKeyboardButton(
                text=f"{emoji} {habit['name']}",
                callback_data=f"habit_{action}_{habit['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )
    return builder.as_markup()


def habit_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа привычки."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔢 Количественная (с числом)",
            callback_data="type_quantity"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Да/Нет (просто отметить)",
            callback_data="type_binary"
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def confirm_delete_keyboard(habit_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления привычки."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🗑 Да, удалить",
            callback_data=f"confirm_delete_{habit_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="back_to_menu"
        )
    )
    return builder.as_markup()


def binary_log_keyboard(habit_id: int) -> InlineKeyboardMarkup:
    """Кнопка для отметки бинарной привычки."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Выполнено!",
            callback_data=f"binary_done_{habit_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="log_habit")
    )
    return builder.as_markup()


def stats_period_keyboard() -> InlineKeyboardMarkup:
    """Выбор периода статистики."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data="stats_today"),
        InlineKeyboardButton(text="📊 Неделя", callback_data="stats_week")
    )
    builder.row(
        InlineKeyboardButton(text="📈 Месяц", callback_data="stats_month")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад в меню."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")
    )
    return builder.as_markup()


def reminder_habits_keyboard(habits: list) -> InlineKeyboardMarkup:
    """Кнопки для быстрого логирования из напоминания."""
    builder = InlineKeyboardBuilder()
    for habit in habits:
        if habit["habit_type"] == "binary":
            builder.row(
                InlineKeyboardButton(
                    text=f"✅ {habit['name']}",
                    callback_data=f"binary_done_{habit['id']}"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text=f"📝 {habit['name']}",
                    callback_data=f"habit_log_{habit['id']}"
                )
            )
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()
