def progress_bar(current: float, target: float, length: int = 10) -> str:
    """Создаёт прогресс-бар из эмодзи.

    Пример: ▓▓▓▓▓▓░░░░ 60%
    """
    if target <= 0:
        return "▓" * length + " 100%"

    ratio = min(current / target, 1.0)
    filled = int(ratio * length)
    empty = length - filled
    percentage = int(ratio * 100)

    bar = "▓" * filled + "░" * empty
    return f"{bar} {percentage}%"


def format_habit_status(name: str, current: float, target: float,
                        unit: str, habit_type: str) -> str:
    """Форматирование статуса привычки для сообщения."""
    if habit_type == "binary":
        if current >= 1:
            return f"✅ {name} — выполнено!"
        else:
            return f"⬜ {name} — не выполнено"

    bar = progress_bar(current, target)
    current_display = int(current) if current == int(current) else current
    target_display = int(target) if target == int(target) else target
    unit_text = f" {unit}" if unit else ""
    return f"{'✅' if current >= target else '🔄'} {name}: {current_display}/{target_display}{unit_text}\n   {bar}"


def format_streak(streak: int) -> str:
    """Форматирование стрика."""
    if streak == 0:
        return "💤 Стрик: 0 дней"
    elif streak < 3:
        return f"🌱 Стрик: {streak} {_days_word(streak)}"
    elif streak < 7:
        return f"🌿 Стрик: {streak} {_days_word(streak)}"
    elif streak < 14:
        return f"🔥 Стрик: {streak} {_days_word(streak)}"
    elif streak < 30:
        return f"🔥🔥 Стрик: {streak} {_days_word(streak)}"
    else:
        return f"🔥🔥🔥 Стрик: {streak} {_days_word(streak)} — ЛЕГЕНДА!"


def _days_word(n: int) -> str:
    """Склонение слова 'день'."""
    if 11 <= n % 100 <= 19:
        return "дней"
    elif n % 10 == 1:
        return "день"
    elif 2 <= n % 10 <= 4:
        return "дня"
    else:
        return "дней"


def format_habit_type_display(habit_type: str) -> str:
    """Отображение типа привычки."""
    return "🔢 Количественная" if habit_type == "quantity" else "✅ Да/Нет"


def format_weekly_stats(habit_name: str, completions: list, target: float,
                        unit: str, habit_type: str, streak: int) -> str:
    """Форматирование недельной статистики."""
    lines = [f"📊 <b>{habit_name}</b>"]
    lines.append(format_streak(streak))
    lines.append("")

    if habit_type == "binary":
        done_count = sum(1 for c in completions if c.get("value", 0) >= 1)
        lines.append(f"За 7 дней: {done_count}/7 выполнено")
        lines.append(progress_bar(done_count, 7))
    else:
        total = sum(c.get("value", 0) for c in completions)
        weekly_target = target * 7
        unit_text = f" {unit}" if unit else ""
        total_display = int(total) if total == int(total) else total
        weekly_target_display = int(weekly_target) if weekly_target == int(weekly_target) else weekly_target
        lines.append(f"За 7 дней: {total_display}/{weekly_target_display}{unit_text}")
        lines.append(progress_bar(total, weekly_target))

    # Мини-календарь за неделю
    from datetime import date, timedelta
    calendar_line = "  "
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        day_completions = [c for c in completions if c.get("completed_at") == d.isoformat()]
        if day_completions:
            value = day_completions[0].get("value", 0)
            if (habit_type == "binary" and value >= 1) or (habit_type == "quantity" and value >= target):
                calendar_line += "🟢"
            elif value > 0:
                calendar_line += "🟡"
            else:
                calendar_line += "🔴"
        else:
            calendar_line += "🔴"
    lines.append(f"\nПоследние 7 дней: {calendar_line}")

    return "\n".join(lines)
