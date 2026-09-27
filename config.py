# Python | config.py | python-telegram-bot 20+ | Telegram cheat-distribution bot

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Список обязательных каналов. username БЕЗ @, или числовой ID (напр. -1001234567890)
REQUIRED_CHANNELS: list[str | int] = [
    "your_channel_username",  # или -1001234567890
    # "second_channel",       # раскомментируй если нужен второй
]

# Telegram user_id администраторов бота
ADMIN_IDS: list[int] = [
    123456789,  # замени на свой Telegram ID
]

# Путь к .exe файлу который бот будет отправлять
EXE_FILE_PATH = "files/cheat.exe"

# Подпись файла которую увидит пользователь
EXE_CAPTION = "✅ Вот твой чит. Удачи, не палить."

# Путь к SQLite базе данных
DB_PATH = "bot.db"
