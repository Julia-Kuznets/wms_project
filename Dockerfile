# Используем официальный легковесный образ Python
FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt /app/

# Устанавливаем библиотеки Python без лишних системных пакетов
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Копируем весь остальной код проекта
COPY . /app/