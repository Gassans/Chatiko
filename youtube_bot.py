import os
import asyncio
import logging
import aiohttp
import re
from googleapiclient.discovery import build
from telegram import Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
YOUTUBE_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]

bot = Bot(token=TELEGRAM_TOKEN)


async def send_message(text):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
    except Exception as e:
        logger.error(f"Ошибка Telegram: {e}")



async def get_live_chat_id(youtube):
    try:
        search = youtube.search().list(
            part='id',
            channelId=YOUTUBE_CHANNEL_ID,
            eventType='live',
            type='video',
            maxResults=1
        ).execute()

        if not search.get('items'):
            return None, None

        video_id = search['items'][0]['id']['videoId']

        details = youtube.videos().list(
            part='liveStreamingDetails',
            id=video_id
        ).execute()

        items = details.get('items')
        if not items:
            return video_id, None

        chat_id = items[0].get('liveStreamingDetails', {}).get('activeLiveChatId')

        return video_id, chat_id

    except Exception as e:
        logger.error(f"Ошибка API: {e}")
        return None, None



async def get_initial_continuation(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()

    match = re.search(r'"continuation":"(.*?)"', html)

    if match:
        return match.group(1)

    return None



async def chat_loop(continuation, seen_users):
    url = "https://www.youtube.com/youtubei/v1/live_chat/get_live_chat"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    is_first_batch = True 

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                payload = {
                    "context": {
                        "client": {
                            "clientName": "WEB",
                            "clientVersion": "2.20210721.00.00"
                        }
                    },
                    "continuation": continuation
                }

                async with session.post(url, json=payload, headers=headers) as resp:
                    data = await resp.json()

                actions = data.get("continuationContents", {}) \
                              .get("liveChatContinuation", {}) \
                              .get("actions", [])

                
                if is_first_batch:
                    logger.info("Пропускаем старые сообщения...")
                    is_first_batch = False
                else:
                    for action in actions:
                        item = action.get("addChatItemAction", {}).get("item", {})
                        message = item.get("liveChatTextMessageRenderer")

                        if not message:
                            continue

                        author_id = message.get("authorExternalChannelId")
                        if not author_id:
                            continue

                        if author_id not in seen_users:
                            seen_users.add(author_id)

                            name = message.get("authorName", {}).get("simpleText", "User")
                            name = name.lstrip('@').strip()

                            await send_message(f"Новый котэк на Ютубе❤️: {name}")

                
                continuations = data.get("continuationContents", {}) \
                                    .get("liveChatContinuation", {}) \
                                    .get("continuations", [])

                if continuations:
                    continuation = continuations[0] \
                        .get("invalidationContinuationData", {}) \
                        .get("continuation") or \
                        continuations[0] \
                        .get("timedContinuationData", {}) \
                        .get("continuation")

                await asyncio.sleep(2)  # ⚡ быстро

            except Exception as e:
                logger.error(f"Ошибка chat_loop: {e}")
                await asyncio.sleep(5)



async def main():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY, static_discovery=False)

    seen_users = set()
    current_video_id = None

    while True:
        try:
            video_id, chat_id = await get_live_chat_id(youtube)

            if not video_id or not chat_id:
                logger.info("Стрим не найден. Ждём 5 минут...")
                await asyncio.sleep(300)
                continue

            
            if video_id != current_video_id:
                logger.info("Новый стрим → очищаем список пользователей")
                seen_users.clear()
                current_video_id = video_id

            logger.info(f"Стрим найден: {video_id}")

            continuation = await get_initial_continuation(video_id)

            if not continuation:
                logger.error("Не удалось получить continuation")
                await asyncio.sleep(60)
                continue

            logger.info("Подключились к чату через youtubei 🔥")

            await chat_loop(continuation, seen_users)

        except Exception as e:
            logger.error(f"Глобальная ошибка: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
