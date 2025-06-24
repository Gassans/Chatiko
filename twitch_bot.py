import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Bot
from twitchio.ext import commands


logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
TWITCH_BOT_TOKEN = os.getenv("TWITCH_BOT_TOKEN")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL")

bot = Bot(token=TELEGRAM_TOKEN)

class TwitchBot(commands.Bot):
    def __init__(self):
        super().__init__(token=TWITCH_BOT_TOKEN, prefix='!', initial_channels=[TWITCH_CHANNEL])
        self.users_in_chat = set()

    async def event_ready(self):
        logging.info(f'TwitchBot готов как {self.nick}')

    async def event_message(self, message):
        if message.author.name.lower() == self.nick.lower():
            return
        if message.author.name not in self.users_in_chat:
            self.users_in_chat.add(message.author.name)
            try:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f'Новый котэк на Твиче💜: {message.author.name}')
            except Exception as e:
                logging.error(f"Ошибка Telegram: {e}")
        await self.handle_commands(message)

async def main():
    twitch_bot = TwitchBot()
    await twitch_bot.start()

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio
    asyncio.run(main())