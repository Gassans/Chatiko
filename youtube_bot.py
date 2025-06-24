import os
import asyncio
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram import Bot

# Настройка логгера
logging.basicConfig(level=logging.INFO)

# Переменные из Replit Secrets
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
YOUTUBE_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]

# Telegram-бот
bot = Bot(token=TELEGRAM_TOKEN)

async def send_message(text):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")

async def get_channel_info(youtube, channel_id):
    try:
        request = youtube.channels().list(part='snippet', id=channel_id)
        response = request.execute()
        if response['items']:
            return response['items'][0]['snippet']['title']
    except HttpError as e:
        logging.error(f'YouTube API error при получении имени: {e}')
    return None

async def get_live_chat_id(youtube, channel_id):
    try:
        request = youtube.search().list(
            part='id',
            channelId=channel_id,
            eventType='live',
            type='video'
        )
        response = request.execute()
        if response['items']:
            video_id = response['items'][0]['id']['videoId']
            details = youtube.videos().list(
                part='liveStreamingDetails',
                id=video_id
            ).execute()
            return details['items'][0]['liveStreamingDetails']['activeLiveChatId']
    except HttpError as e:
        logging.error(f'YouTube API error при получении liveChatId: {e}')
    return None

async def youtube_bot_loop():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    seen_users = set()

    while True:
        live_chat_id = await get_live_chat_id(youtube, YOUTUBE_CHANNEL_ID)
        if not live_chat_id:
            logging.info("Стрим не найден. Следующая попытка через 5 минут.")
            await asyncio.sleep(300)
            continue

        logging.info(f"Подключено к YouTube чату: {live_chat_id}")
        next_page_token = None

        while True:
            try:
                request = youtube.liveChatMessages().list(
                    liveChatId=live_chat_id,
                    part='snippet',
                    pageToken=next_page_token
                )
                response = request.execute()
                messages = response.get('items', [])
                next_page_token = response.get('nextPageToken')

                for message in messages:
                    author_id = message['snippet']['authorChannelId']
                    if author_id not in seen_users:
                        seen_users.add(author_id)
                        user_name = await get_channel_info(youtube, author_id)
                        if user_name:
                            await send_message(f"Новый котэк на Ютубе❤️: {user_name}")

                await asyncio.sleep(30)

            except HttpError as e:
                logging.error(f"Ошибка YouTube API в цикле чата: {e}")
                break

if __name__ == "__main__":
    asyncio.run(youtube_bot_loop())