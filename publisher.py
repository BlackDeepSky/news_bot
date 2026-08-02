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


def post_news(chat_id, title, summary, url, image_url):
    """Публикует новость в канал. Если Telegram не смог обработать фото
    (битая ссылка, недоступный хост) — отправляет тот же текст без фото,
    вместо того чтобы терять новость."""
    if image_url:
        caption = _build_caption(title, summary, url, max_length=1024)
        try:
            response = requests.post(
                f'{API_URL}/sendPhoto',
                data={'chat_id': chat_id, 'photo': image_url, 'caption': caption, 'parse_mode': 'HTML'},
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
