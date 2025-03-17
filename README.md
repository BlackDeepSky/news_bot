# Telegram News Bot
Бот для Telegram, который собирает новости с NewsAPI, суммирует их и отправляет администратору для публикации в канале.

## Установка
1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/telegram-news-bot.git
   cd telegram-news-bot
   ```
2.Создайте виртуальное окружение и установите зависимости:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
Для сервера без GPU:
torch --index-url https://download.pytorch.org/whl/cpu

3.Создайте файл .env с вашими настройками (см. пример ниже).
4.Запустите бота:
```bash
python bot.py
```
