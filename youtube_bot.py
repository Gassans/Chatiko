import os
import asyncio
import logging
import pytchat
from googleapiclient.discovery import build
from telegram import Bot

logging.basicConfig(level=logging.INFO)

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
            type='video',
            order='date',
            maxResults=5
        )
        response = request.execute()

        for item in response['items']:
            video_id = item['id']['videoId']

            video_request = youtube.videos().list(
                part='liveStreamingDetails',
                id=video_id
            )
            video_response = video_request.execute()

            if not video_response['items']:
                continue

            details = video_response['items'][0].get('liveStreamingDetails', {})

            # если стрим уже начался и не закончился
            if 'actualStartTime' in details and 'actualEndTime' not in details:
                logging.info(f"Найден live стрим: {video_id}")
                return video_id

    except Exception as e:
        logging.error(f"Ошибка получения live video: {e}")

    return None


async def youtube_bot_loop():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    seen_users = set()

    while True:
        try:
            video_id = await get_live_video_id(youtube, YOUTUBE_CHANNEL_ID)

            if not video_id:
                logging.info("Стрим не найден. Проверка через 2 минуты.")
                await asyncio.sleep(120)
                continue

            logging.info(f"Подключение к чату: {video_id}")

            await asyncio.sleep(5)

            chat = None
            for _ in range(5):
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

            while chat.is_alive():
                try:
                    for c in chat.get().sync_items():
                        author_id = c.author.channelId

                        if author_id not in seen_users:
                            seen_users.add(author_id)
                            user_name = c.author.name.lstrip('@').strip()
                            await send_message(f"Новый котэк на Ютубе❤️: {user_name}")

                    await asyncio.sleep(1)

                except Exception as e:
                    logging.error(f"Ошибка чтения чата: {e}")
                    await asyncio.sleep(5)

            logging.info("Чат завершён. Повторная проверка через 1 минуту.")
            await asyncio.sleep(60)

        except Exception as e:
            logging.error(f"Глобальная ошибка: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(youtube_bot_loop())
