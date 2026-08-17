import html
import re

import requests
from loguru import logger

from config import BOT_TOKEN

API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'


def _normalize_tags(category, tags, max_tags=3):
    """Собирает финальный список хэштегов поста: обязательный тег категории
    источника (из FEEDS — «ИИ», «Наука» и т.п.) плюс до двух тем от модели.
    Модель иногда пишет лишние '#' или дублирует категорию — чистим и
    дедуплицируем без учёта регистра, чтобы в канал не уходили '#ИИ #ии'.
    Хэштеги — единственная часть поста, которую Telegram индексирует как
    поисковые метки, поэтому категория добавляется всегда, даже если модель
    теги не выдала."""
    seen = set()
    result = []

    def add(tag):
        key = tag.strip().lstrip('#').lower()
        if key and key not in seen:
            seen.add(key)
            result.append(f'#{tag.strip().lstrip("#")}')

    if category:
        add(category)

    if tags:
        for tag in re.split(r'[,\s]+', tags):
            add(tag)
            if len(result) >= max_tags:
                break

    return result


def _build_caption(title, summary, url, tags, max_length):
    # HTML вместо Markdown: html.escape() корректно экранирует весь текст
    # одной функцией, тогда как ручное экранирование '*_[]`' (как было раньше)
    # легко пропустить в одном из двух мест отправки и получить упавший запрос.
    # Хэштеги в конец поста, а не в начало: поиск Telegram смотрит весь текст,
    # а начало занимают заголовок и выжимка, которые видно в превью.
    prefix = f"<b>{html.escape(title)}</b>\n\n"
    suffix = f'\n\n<a href="{html.escape(url)}">Читать полностью</a>'
    if tags:
        suffix += '\n\n' + ' '.join(html.escape(tag) for tag in tags)

    # Обрезаем только выжимку — и до экранирования. Раньше резали готовый HTML
    #     целиком: caption упирался в лимит 1024, и обрезка могла перерезать тег
    # `<a href="...` пополам — Telegram отвечал 400 "Unclosed start tag" и пост
    # уходил без фото. html.escape() удлиняет текст (например, `&` -> `&amp;`),
    # поэтому после обрезки проверяем реальную длину и ужимаем ещё раз.
    summary = summary[:max_length - len(prefix) - len(suffix)]
    while html.escape(summary) and len(html.escape(summary)) > max_length - len(prefix) - len(suffix):
        summary = summary[:-1]
    return prefix + html.escape(summary) + suffix


def post_news(chat_id, title, summary, url, image_bytes, category='',
              tags='', image_content_type='image/jpeg'):
    """Публикует новость в канал. Картинка отправляется байтами (multipart),
    а не ссылкой — Telegram принимает файл напрямую и не зависит от того,
    доступен ли внешний хост в момент публикации. Если Telegram не смог
    обработать фото — отправляем тот же текст без фото, чтобы не терять
    новость полностью."""
    hashtags = _normalize_tags(category, tags)
    if image_bytes:
        caption = _build_caption(title, summary, url, hashtags, max_length=1024)
        try:
            response = requests.post(
                f'{API_URL}/sendPhoto',
                data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'},
                files={'photo': ('news.jpg', image_bytes, image_content_type)},
                timeout=30,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"Не удалось отправить фото ({e}), пробую текстом")

    text = _build_caption(title, summary, url, hashtags, max_length=4096)
    try:
        response = requests.post(
            f'{API_URL}/sendMessage',
            data={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
            timeout=30,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки в Telegram: {e}")
        return False
