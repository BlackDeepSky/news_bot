# Telegram News Bot

Бот собирает новости из RSS-лент про ИИ, робототехнику, науку, программирование
и ИТ, пересказывает их по-русски через бесплатную модель на OpenRouter и
публикует в Telegram-канал. Работает без постоянно работающего сервера —
запускается по расписанию через GitHub Actions.

## Архитектура

```
feeds.py      -> читает RSS-ленты (feedparser)
extractor.py  -> достаёт текст статьи и og:image со страницы (trafilatura)
ai.py         -> переводит+суммирует+даёт описание для картинки одним запросом к OpenRouter
pexels.py     -> ищет стоковое фото по теме статьи (Pexels API)
image_gen.py  -> рисует картинку сам, если больше неоткуда взять (Pollinations.ai)
database.py   -> SQLite-файл news.db — какие статьи уже публиковали
publisher.py  -> публикует в канал напрямую через Telegram Bot API
main.py       -> связывает всё вместе, разовый прогон
```

Картинка к посту ищется по цепочке от самого достоверного источника к самому
крайнему: картинка из RSS → `og:image` со страницы статьи → стоковое фото по
теме на Pexels → и только если ничего не нашлось — рисуем сами через ИИ.

Никакого постоянно работающего процесса нет: `main.py` — это одноразовый
скрипт, который делает один проход по всем источникам и завершается. Между
запусками состояние (какие статьи уже публиковались) хранится в `news.db`,
который воркфлоу коммитит обратно в репозиторий — GitHub Actions раннер
эфемерный и ничего не помнит между запусками сам по себе.

## Настройка

### 1. Telegram-бот

1. Создайте бота через [@BotFather](https://t.me/BotFather), получите `BOT_TOKEN`.
2. Добавьте бота администратором в канал, куда он будет постить.
3. `CHANNEL_ID` — это `@username_канала` (для публичных) или числовой ID вида
   `-100xxxxxxxxxx` (для приватных — его можно узнать, например, через
   [@userinfobot](https://t.me/userinfobot) или переслав сообщение из канала боту вроде @JsonDumpBot).

### 2. OpenRouter (бесплатный ИИ)

1. Зарегистрируйтесь на [openrouter.ai](https://openrouter.ai) — только email,
   карта не нужна для бесплатных моделей.
2. Создайте API-ключ (`OPENROUTER_API_KEY`).
3. Без пополнения баланса действует ограниченная дневная квота запросов
   (см. свой dashboard на сайте) — под неё настроены `MAX_ARTICLES_PER_RUN`
   и `MAX_ARTICLES_PER_FEED` в `config.py`.
4. Список бесплатных моделей (`OPENROUTER_MODEL` в `config.py`) периодически
   меняется — актуальный: https://openrouter.ai/models?max_price=0

### 3. Pexels (бесплатные стоковые фото)

1. Зарегистрируйтесь на [pexels.com/api](https://www.pexels.com/api/) —
   только email, карта не нужна, ключ выдаётся сразу без модерации.
2. Получите API-ключ (`PEXELS_API_KEY`).

### 4. Запуск через GitHub Actions (рекомендуется)

1. Запушьте репозиторий на GitHub.
2. В Settings → Secrets and variables → Actions добавьте четыре секрета:
   `BOT_TOKEN`, `CHANNEL_ID`, `OPENROUTER_API_KEY`, `PEXELS_API_KEY`.
3. Убедитесь, что в Settings → Actions → General → Workflow permissions
   включено "Read and write permissions" — воркфлоу коммитит `news.db`
   обратно в репозиторий.
4. Воркфлоу `.github/workflows/post_news.yml` запускается по расписанию
   (каждые 3 часа) и вручную — вкладка Actions → Post news → Run workflow.

### 5. Локальный запуск (для отладки)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # и вписать реальные значения
python main.py
```
