import os
import asyncio
import logging
from googleapiclient.discovery import build
from telegram import Bot

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
YOUTUBE_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]

bot = Bot(token=TELEGRAM_TOKEN)

async def send_message(text):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
        logger.info(f"ТГ уведомление отправлено")
    except Exception as e:
        logger.error(f"Ошибка ТГ: {e}")

async def get_live_info(youtube):
    """Ищет стрим и ID чата. Тратит ~101 юнит квоты."""
    try:
        # 1. Ищем ID видео
        search = youtube.search().list(
            part='id', 
            channelId=YOUTUBE_CHANNEL_ID, 
            eventType='live', 
            type='video'
        ).execute()
        
        if not search.get('items'):
            return None, None
        
        video_id = search['items'][0]['id']['videoId']
        
        # 2. Получаем ID чата для этого видео
        video_details = youtube.videos().list(
            part='liveStreamingDetails', 
            id=video_id
        ).execute()
        
        chat_id = video_details['items'][0].get('liveStreamingDetails', {}).get('activeLiveChatId')
        return video_id, chat_id
    except Exception as e:
        logger.error(f"Ошибка API при поиске: {e}")
        return None, None

async def youtube_bot_loop():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY, static_discovery=False)
    seen_users = set()
    
    while True:
        try:
            # Находим стрим
            video_id, live_chat_id = await get_live_info(youtube)
            
            if not video_id or not live_chat_id:
                logger.info("Стрим не найден. Проверка через 5 минут (квота сохранена).")
                await asyncio.sleep(300)
                continue

            logger.info(f"Подключено к API чату: {live_chat_id}")
            next_page_token = None

            # Цикл чтения сообщений (1 запрос = 1 юнит)
            while True:
                try:
                    request = youtube.liveChatMessages().list(
                        liveChatId=live_chat_id,
                        part='snippet,authorDetails',
                        pageToken=next_page_token
                    )
                    response = request.execute()
                    
                    for item in response.get('items', []):
                        author_id = item['authorDetails']['channelId']
                        if author_id not in seen_users:
                            seen_users.add(author_id)
                            user_name = item['authorDetails']['displayName']
                            await send_message(f"Новый котэк на Ютубе❤️: {user_name}")

                    next_page_token = response.get('nextPageToken')
                    
                    # Интервал 10 секунд (баланс между скоростью и квотами)
                    await asyncio.sleep(10)

                except Exception as e:
                    # Если стрим кончился или ошибка токена
                    logger.error(f"Чат завершен или ошибка: {e}")
                    next_page_token = None
                    break 

        except Exception as e:
            logger.error(f"Глобальная ошибка: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(youtube_bot_loop())
