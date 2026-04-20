import aiosqlite
from config import DB_PATH, DEFAULT_REMINDER_TIME, DEFAULT_TIMEZONE
from datetime import date, timedelta
from typing import Optional


async def init_db():
    """Создание таблиц при первом запуске."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                reminder_time TEXT DEFAULT '09:00',
                timezone TEXT DEFAULT 'Asia/Novosibirsk',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                habit_type TEXT DEFAULT 'quantity',
                target_value REAL DEFAULT 1,
                unit TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER,
                user_id INTEGER,
                value REAL DEFAULT 1,
                completed_at DATE DEFAULT (date('now')),
                FOREIGN KEY (habit_id) REFERENCES habits(id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()


# ============ USERS ============

async def add_user(user_id: int, username: str, first_name: str):
    """Регистрация пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users (user_id, username, first_name, reminder_time, timezone)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, first_name, DEFAULT_REMINDER_TIME, DEFAULT_TIMEZONE)
        )
        await db.commit()


async def get_user(user_id: int) -> Optional[dict]:
    """Получить данные пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def update_reminder_time(user_id: int, time_str: str):
    """Обновить время напоминания."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET reminder_time = ? WHERE user_id = ?",
            (time_str, user_id)
        )
        await db.commit()


async def get_all_users() -> list[dict]:
    """Получить всех пользователей (для напоминаний)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ============ HABITS ============

async def add_habit(user_id: int, name: str, habit_type: str = "quantity",
                    target_value: float = 1, unit: str = "") -> int:
    """Добавить привычку. Возвращает ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO habits (user_id, name, habit_type, target_value, unit)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, name, habit_type, target_value, unit)
        )
        await db.commit()
        return cursor.lastrowid


async def get_habits(user_id: int, active_only: bool = True) -> list[dict]:
    """Получить привычки пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM habits WHERE user_id = ?"
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY created_at"
        cursor = await db.execute(query, (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_habit_by_id(habit_id: int) -> Optional[dict]:
    """Получить привычку по ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM habits WHERE id = ?", (habit_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def delete_habit(habit_id: int):
    """Деактивировать привычку (мягкое удаление)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE habits SET is_active = 0 WHERE id = ?", (habit_id,)
        )
        await db.commit()


# ============ COMPLETIONS ============

async def log_completion(habit_id: int, user_id: int, value: float = 1,
                         target_date: Optional[str] = None):
    """Залогировать выполнение привычки."""
    async with aiosqlite.connect(DB_PATH) as db:
        if target_date is None:
            target_date = date.today().isoformat()

        # Проверяем, есть ли уже запись за сегодня
        cursor = await db.execute(
            """SELECT id, value FROM completions
               WHERE habit_id = ? AND user_id = ? AND completed_at = ?""",
            (habit_id, user_id, target_date)
        )
        existing = await cursor.fetchone()

        if existing:
            # Обновляем существующую запись (прибавляем значение)
            new_value = existing[1] + value
            await db.execute(
                "UPDATE completions SET value = ? WHERE id = ?",
                (new_value, existing[0])
            )
        else:
            await db.execute(
                """INSERT INTO completions (habit_id, user_id, value, completed_at)
                   VALUES (?, ?, ?, ?)""",
                (habit_id, user_id, value, target_date)
            )
        await db.commit()


async def get_today_completions(user_id: int) -> list[dict]:
    """Получить все логи за сегодня."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        today = date.today().isoformat()
        cursor = await db.execute(
            """SELECT c.*, h.name, h.target_value, h.unit, h.habit_type
               FROM completions c
               JOIN habits h ON c.habit_id = h.id
               WHERE c.user_id = ? AND c.completed_at = ?""",
            (user_id, today)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_habit_completion_today(habit_id: int, user_id: int) -> Optional[dict]:
    """Получить лог привычки за сегодня."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        today = date.today().isoformat()
        cursor = await db.execute(
            """SELECT * FROM completions
               WHERE habit_id = ? AND user_id = ? AND completed_at = ?""",
            (habit_id, user_id, today)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def get_completions_for_period(habit_id: int, user_id: int,
                                     days: int = 7) -> list[dict]:
    """Получить логи за период (последние N дней)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        start_date = (date.today() - timedelta(days=days)).isoformat()
        cursor = await db.execute(
            """SELECT * FROM completions
               WHERE habit_id = ? AND user_id = ? AND completed_at >= ?
               ORDER BY completed_at""",
            (habit_id, user_id, start_date)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_streak(habit_id: int, user_id: int) -> int:
    """Подсчёт текущего стрика (дней подряд)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT DISTINCT completed_at FROM completions
               WHERE habit_id = ? AND user_id = ?
               ORDER BY completed_at DESC""",
            (habit_id, user_id)
        )
        rows = await cursor.fetchall()

        if not rows:
            return 0

        streak = 0
        check_date = date.today()

        for row in rows:
            completion_date = date.fromisoformat(row[0])
            if completion_date == check_date:
                streak += 1
                check_date -= timedelta(days=1)
            elif completion_date == check_date - timedelta(days=1):
                # Пропустили сегодня, но вчера было — считаем
                check_date = completion_date
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        return streak


async def get_uncompleted_habits(user_id: int) -> list[dict]:
    """Получить привычки, которые ещё не отмечены сегодня."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        today = date.today().isoformat()
        cursor = await db.execute(
            """SELECT h.* FROM habits h
               WHERE h.user_id = ? AND h.is_active = 1
               AND h.id NOT IN (
                   SELECT habit_id FROM completions
                   WHERE user_id = ? AND completed_at = ?
                   AND value >= h.target_value
               )""",
            (user_id, user_id, today)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
