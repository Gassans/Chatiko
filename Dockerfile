# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем необходимые системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . /app

# Устанавливаем зависимости из requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем nest_asyncio (если ты его используешь для Twitch-бота)
RUN pip install nest_asyncio

# Указываем команду запуска (запускай нужный бот по умолчанию)
CMD ["python", "main.py"]
