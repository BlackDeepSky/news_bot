import html

import requests
from loguru import logger

from config import BOT_TOKEN

API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'


def _truncate(text, max_length):
    if len(text) > max_length:
        return text[:max_length - 3] + '...'
    return text


def _build_caption(title, summary, url, max_length):
    # HTML вместо Markdown: html.escape() корректно экранирует весь текст
    # одной функцией, тогда как ручное экранирование '*_[]`' (как было раньше)
    # легко пропустить в одном из двух мест отправки и получить упавший запрос.
    caption = (
        f"<b>{html.escape(title)}</b>\n\n"
        f"{html.escape(summary)}\n\n"
        f'<a href="{html.escape(url)}">Читать полностью</a>'
    )
    return _truncate(caption, max_length)


def post_news(chat_id, title, summary, url, image_bytes, image_content_type='image/jpeg'):
    """Публикует новость в канал. Картинка отправляется байтами (multipart),
    а не ссылкой — Telegram принимает файл напрямую и не зависит от того,
    доступен ли внешний хост в момент публикации. Если Telegram не смог
    обработать фото — отправляем тот же текст без фото, чтобы не терять
    новость полностью."""
    if image_bytes:
        caption = _build_caption(title, summary, url, max_length=1024)
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

    text = _build_caption(title, summary, url, max_length=4096)
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
