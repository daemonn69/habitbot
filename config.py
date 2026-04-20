import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Поддержка Railway Volume — если задана переменная DB_PATH, используем её
# Иначе создаём habits.db рядом с bot.py
_db_path_env = os.getenv("DB_PATH")
if _db_path_env:
    DB_PATH = _db_path_env
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "habits.db")

DEFAULT_REMINDER_TIME = "09:00"
DEFAULT_TIMEZONE = "Asia/Novosibirsk"
