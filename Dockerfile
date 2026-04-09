FROM python:3.10-slim

# Устанавливаем необходимые системные пакеты
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Обновляем pip и ставим зависимости
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

CMD ["python", "main.py"]
