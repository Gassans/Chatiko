import os
import asyncio
import logging
import aiohttp
import json
from googleapiclient.discovery import build
from telegram import Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
YOUTUBE_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]

bot = Bot(token=TELEGRAM_TOKEN)


# ------------------ TELEGRAM ------------------
async def send_message(text):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
    except Exception as e:
        logger.error(f"Telegram error: {e}")


# ------------------ YOUTUBE API ------------------
async def get_video_and_chat(youtube):
    try:
        # live + upcoming (премьеры тоже тут)
        req = youtube.search().list(
            part="id",
            channelId=YOUTUBE_CHANNEL_ID,
            type="video",
            eventType="live",
            maxResults=1
        ).execute()

        video_id = None

        if req.get("items"):
            video_id = req["items"][0]["id"]["videoId"]

        # fallback: upcoming (премьеры)
        if not video_id:
            req2 = youtube.search().list(
                part="id",
                channelId=YOUTUBE_CHANNEL_ID,
                type="video",
                eventType="upcoming",
                maxResults=1
            ).execute()

            if req2.get("items"):
                video_id = req2["items"][0]["id"]["videoId"]

        if not video_id:
            return None, None

        # получаем liveChatId
        details = youtube.videos().list(
            part="liveStreamingDetails",
            id=video_id
        ).execute()

        items = details.get("items", [])
        if not items:
            return video_id, None

        chat_id = items[0].get("liveStreamingDetails", {}).get("activeLiveChatId")

        return video_id, chat_id

    except Exception as e:
        logger.error(f"YouTube API error: {e}")
        return None, None


# ------------------ CHAT WORKER ------------------
async def chat_worker(live_chat_id, seen_users):
    url = "https://www.youtube.com/youtubei/v1/live_chat/get_live_chat"
    headers = {"Content-Type": "application/json"}

    continuation = None
    is_first = True

    async with aiohttp.ClientSession() as session:

        # 🔥 получаем стартовую continuation
        init_payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20210721"
                }
            },
            "continuation": live_chat_id
        }

        async with session.post(url, json=init_payload, headers=headers) as r:
            data = await r.json()

        continuations = data.get("continuationContents", {}) \
                            .get("liveChatContinuation", {}) \
                            .get("continuations", [])

        if continuations:
            continuation = continuations[0].get("invalidationContinuationData", {}).get("continuation")

        if not continuation:
            raise Exception("No continuation yet (premiere not ready)")

        logger.info("Chat connected")

        while True:
            try:
                payload = {
                    "context": {
                        "client": {
                            "clientName": "WEB",
                            "clientVersion": "2.20210721"
                        }
                    },
                    "continuation": continuation
                }

                async with session.post(url, json=payload, headers=headers) as r:
                    data = await r.json()

                actions = data.get("continuationContents", {}) \
                              .get("liveChatContinuation", {}) \
                              .get("actions", [])

                # 🔥 ПРОПУСК ИСТОРИИ
                if is_first:
                    is_first = False
                else:
                    for action in actions:
                        msg = action.get("addChatItemAction", {}).get("item", {}) \
                                    .get("liveChatTextMessageRenderer")

                        if not msg:
                            continue

                        author_id = msg.get("authorExternalChannelId")

                        if author_id and author_id not in seen_users:
                            seen_users.add(author_id)

                            name = msg.get("authorName", {}).get("simpleText", "User")

                            await send_message(f"Новый котэк ❤️: {name}")

                # 🔁 обновляем continuation
                conts = data.get("continuationContents", {}) \
                            .get("liveChatContinuation", {}) \
                            .get("continuations", [])

                if conts:
                    continuation = (
                        conts[0].get("invalidationContinuationData", {}).get("continuation")
                        or conts[0].get("timedContinuationData", {}).get("continuation")
                    )

                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Chat error: {e}")
                await asyncio.sleep(3)


# ------------------ MAIN LOOP ------------------
async def main():
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY, static_discovery=False)

    seen_users = set()
    current_video = None

    while True:
        try:
            video_id, chat_id = await get_video_and_chat(youtube)

            if not video_id:
                logger.info("No stream/premiere. Sleep 5 min")
                await asyncio.sleep(300)
                continue

            # 🔥 обновление стрима
            if video_id != current_video:
                logger.info("New stream detected")
                seen_users.clear()
                current_video = video_id

            logger.info(f"Video: {video_id}")

            # ⚠️ если премьера ещё не активировала чат
            if not chat_id:
                logger.info("Chat not ready yet (premiere). retry in 20 sec")
                await asyncio.sleep(20)
                continue

            logger.info("Chat ready, connecting...")

            await chat_worker(chat_id, seen_users)

        except Exception as e:
            logger.error(f"Main error: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
