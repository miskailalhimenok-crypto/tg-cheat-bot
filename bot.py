# Python | bot.py | python-telegram-bot 20.x | Main bot entry point

import logging
import os
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.error import TelegramError

import config
import database as db
from keep_alive import keep_alive

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def check_subscriptions(bot, user_id: int) -> list[str | int]:
    """Возвращает список каналов на которые пользователь НЕ подписан."""
    not_subscribed: list[str | int] = []
    for channel in config.REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=f"@{channel}" if isinstance(channel, str) else channel, user_id=user_id)
            if member.status in (ChatMember.LEFT, ChatMember.BANNED):
                not_subscribed.append(channel)
        except TelegramError:
            # канал недоступен боту — считаем что не подписан
            not_subscribed.append(channel)
    return not_subscribed


def build_subscribe_keyboard() -> InlineKeyboardMarkup:
    """Кнопки для подписки на каналы + кнопка проверки."""
    buttons = []
    for ch in config.REQUIRED_CHANNELS:
        if isinstance(ch, str):
            url = f"https://t.me/{ch}"
            label = f"📢 @{ch}"
        else:
            url = f"https://t.me/c/{str(ch).replace('-100', '')}"
            label = f"📢 Канал {ch}"
        buttons.append([InlineKeyboardButton(label, url=url)])
    buttons.append([InlineKeyboardButton("✅ Я подписался — проверить", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name)

    not_sub = await check_subscriptions(ctx.bot, user.id)

    if not_sub:
        await update.message.reply_text(
            f"👋 Привет, *{user.first_name}*!\n\n"
            "Чтобы получить файл — подпишись на каналы ниже.\n"
            "После подписки нажми кнопку проверки.",
            parse_mode="Markdown",
            reply_markup=build_subscribe_keyboard(),
        )
        return

    await send_file(update.message, ctx, user.id)


async def check_sub_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = query.from_user
    db.upsert_user(user.id, user.username, user.first_name)

    not_sub = await check_subscriptions(ctx.bot, user.id)

    if not_sub:
        names = ", ".join(f"@{c}" if isinstance(c, str) else str(c) for c in not_sub)
        await query.edit_message_text(
            f"❌ Ты ещё не подписан на: {names}\n\nПодпишись и нажми кнопку снова.",
            reply_markup=build_subscribe_keyboard(),
        )
        return

    # подписан — отправляем файл
    await query.edit_message_text("⏳ Подписка подтверждена, отправляю файл...")
    await send_file(query.message, ctx, user.id)


async def send_file(message, ctx: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    exe_path = Path(config.EXE_FILE_PATH)

    if not exe_path.exists():
        await message.reply_text(
            "⚠️ Файл временно недоступен. Обратись к администратору."
        )
        logger.error(f"EXE file not found: {exe_path.absolute()}")
        return

    already_got = db.has_got_file(user_id)

    with open(exe_path, "rb") as f:
        await ctx.bot.send_document(
            chat_id=user_id,
            document=f,
            filename=exe_path.name,
            caption=config.EXE_CAPTION,
        )

    if not already_got:
        db.mark_got_file(user_id)
        logger.info(f"File sent to new user {user_id}")
    else:
        logger.info(f"File re-sent to user {user_id}")


# ---------------------------------------------------------------------------
# Admin commands
# ---------------------------------------------------------------------------

def admin_only(func):
    """Декоратор — только для админов."""
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in config.ADMIN_IDS:
            await update.message.reply_text("🚫 Нет доступа.")
            return
        return await func(update, ctx)
    return wrapper


@admin_only
async def stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    s = db.get_stats()
    await update.message.reply_text(
        f"📊 *Статистика*\n\n"
        f"👥 Всего пользователей: `{s['total_users']}`\n"
        f"📥 Получили файл: `{s['got_file']}`\n"
        f"📅 Скачиваний сегодня: `{s['downloads_today']}`",
        parse_mode="Markdown",
    )


@admin_only
async def broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Использование: /broadcast Текст сообщения"""
    if not ctx.args:
        await update.message.reply_text("Укажи текст: /broadcast Привет всем!")
        return

    text = " ".join(ctx.args)
    users = db.get_all_users()
    sent = 0
    failed = 0

    for uid in users:
        try:
            await ctx.bot.send_message(chat_id=uid, text=text)
            sent += 1
        except TelegramError:
            failed += 1

    await update.message.reply_text(
        f"📢 Рассылка завершена.\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}"
    )


@admin_only
async def set_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Загрузить новый .exe файл через бота. Просто прикрепи файл и напиши /set_file."""
    if not update.message.document:
        await update.message.reply_text("Прикрепи .exe файл вместе с командой /set_file")
        return

    doc = update.message.document
    os.makedirs(Path(config.EXE_FILE_PATH).parent, exist_ok=True)
    file = await ctx.bot.get_file(doc.file_id)
    await file.download_to_drive(config.EXE_FILE_PATH)

    await update.message.reply_text(f"✅ Файл сохранён как `{config.EXE_FILE_PATH}`", parse_mode="Markdown")
    logger.info(f"Admin {update.effective_user.id} updated exe file.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    db.init_db()
    os.makedirs(Path(config.EXE_FILE_PATH).parent, exist_ok=True)
    keep_alive()  # HTTP ping-сервер на порту 8080, Render не засыпает

    app = Application.builder().token(config.BOT_TOKEN).build()

    # User handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))

    # Admin handlers
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(
        MessageHandler(filters.Document.ALL & filters.COMMAND, set_file)
    )
    app.add_handler(CommandHandler("set_file", set_file))

    logger.info("Bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
