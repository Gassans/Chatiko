import subprocess
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from keep_alive import keep_alive

processes = {}

auto_stop_task = None

AUTO_STOP_SECONDS = 10 * 3600

async def auto_stop(context: ContextTypes.DEFAULT_TYPE):
    global processes, auto_stop_task
    if processes:
        for p in processes.values():
            p.terminate()
        processes = {}
        auto_stop_task = None
        chat_id = context.job.chat_id
        await context.bot.send_message(chat_id, "Бот остановлен по таймеру")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["✅ Старт", "⛔ Стоп"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привет! Выбери действие:", reply_markup=markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global processes, auto_stop_task
    text = update.message.text
    chat_id = update.effective_chat.id

    if text == "✅ Старт":
        if processes:
            await update.message.reply_text("Бот уже запущен")
            return
        processes['youtube'] = subprocess.Popen(['python3', 'youtube_bot.py'])
        processes['twitch'] = subprocess.Popen(['python3', 'twitch_bot.py'])
        await update.message.reply_text("Бот запущен!")

        # Запускаем таймер авто-стопа
        if auto_stop_task:
            auto_stop_task.schedule_removal()  # Отменяем старый таймер, если есть
        auto_stop_task = context.job_queue.run_once(auto_stop, AUTO_STOP_SECONDS, chat_id=chat_id)

    elif text == "⛔ Стоп":
        if not processes:
            await update.message.reply_text("Бот не работает")
            return
        for p in processes.values():
            p.terminate()
        processes = {}
        await update.message.reply_text("Бот остановлен")
        # Отменяем таймер авто-стопа
        if auto_stop_task:
            auto_stop_task.schedule_removal()
            auto_stop_task = None

async def main():
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    await app.run_polling()

if __name__ == '__main__':
    keep_alive()
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio
    asyncio.run(main())