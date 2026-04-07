import os
import asyncio
import logging
import pytchat
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram import Bot

# Логирование
logging.basicConfig(level=logging.INFO)

# Переменные окружения
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
YOUTUBE_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]

bot = Bot(token=TELEGRAM_TOKEN)


async def send_message(text):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")


async def get_live_video_id(youtube, channel_id):
    try:
        request = youtube.search().list(
            part='id',
            channelId=channel_id,
            eventType='live',
            type='video'
        )
        response = request.execute()
        if response['items']:
            return response['items'][0]['id']['videoId']
    except HttpError as e:
        logging.error(f"Ошибка YouTube API при получении live video: {e}")
    return None


async def youtube_bot_loop():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    seen_users = set()

    while True:
        try:
            video_id = await get_live_video_id(youtube, YOUTUBE_CHANNEL_ID)

            if not video_id:
                logging.info("Стрим не найден. Следующая проверка через 5 минут.")
                await asyncio.sleep(300)
                continue

            logging.info(f"Подключение к YouTube чату видео: {video_id}")

            # небольшая задержка (важно для стабильности pytchat)
            await asyncio.sleep(5)

            # retry подключения к чату
            chat = None
            for _ in range(3):
                try:
                    chat = pytchat.create(video_id=video_id)
                    break
                except Exception as e:
                    logging.error(f"Ошибка подключения к чату: {e}")
                    await asyncio.sleep(5)

            if not chat:
                logging.error("Не удалось подключиться к чату. Повтор через 1 минуту.")
                await asyncio.sleep(60)
                continue

            # читаем чат
            while chat.is_alive():
                try:
                    for c in chat.get().sync_items():
                        author_id = c.author.channelId

                        if author_id not in seen_users:
                            seen_users.add(author_id)

                            # используем имя напрямую (без API!)
                            user_name = c.author.name

                            await send_message(f"Новый котэк на Ютубе❤️: {user_name}")

                    await asyncio.sleep(1)

                except Exception as e:
                    logging.error(f"Ошибка в чтении чата: {e}")
                    await asyncio.sleep(5)

            logging.info("Чат завершен. Проверка нового стрима через 1 минуту.")
            await asyncio.sleep(60)

        except Exception as e:
            logging.error(f"Глобальная ошибка цикла: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(youtube_bot_loop())
