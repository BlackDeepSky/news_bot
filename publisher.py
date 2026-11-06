import html
import json
import re

import requests
from loguru import logger

from config import BOT_TOKEN

API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

# Порог, ниже которого выжимка перестаёт быть выжимкой. Если блок «Почему это
# важно» съедает столько места, что от текста статьи остаётся меньше, блок
# отбрасывается: пост без редакторской ремарки полезнее поста без новости.
MIN_SUMMARY_BUDGET = 200

# Лимиты Bot API для опроса: вопрос до 300 символов, вариант до 100, от 2 до 10
# вариантов. Это факты о платформе, а не настройки канала, поэтому живут здесь,
# а не в config.py. Четыре варианта — наш потолок: вопрос «Да/Нет/Сложнее» на
# телефоне читается, а восемь кнопок — уже простыня.
POLL_QUESTION_LIMIT = 300
POLL_OPTION_LIMIT = 100
POLL_MIN_OPTIONS = 2
POLL_MAX_OPTIONS = 4


def _ok(response):
    """True, если Telegram действительно принял сообщение. raise_for_status()
    ловит только HTTP-ошибки, но Bot API на бизнес-ошибку (битая HTML-разметка,
    неверный chat_id) отвечает HTTP 200 с полем ok: false — без этой проверки
    отправка считалась бы успешной, хотя ничего не ушло."""
    return response.json().get('ok') is True


def _normalize_tags(category, tags, max_tags=3):
    """Собирает финальный список хэштегов поста. Публикуется только тег
    категории источника (из FEEDS — «ИИ», «Наука» и т.п.); теги от модели в
    main.py больше не передаются — они нестабильны и шумят. Хэштеги —
    единственная часть поста, которую Telegram индексирует как поисковые
    метки, поэтому категория добавляется всегда."""
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


def _message_id(response):
    """message_id отправленного сообщения — он нужен, чтобы опрос прицепить
    ответом на пост. None, если Telegram его не вернул (тогда опрос уйдёт
    отдельным сообщением или не уйдёт вовсе)."""
    result = response.json().get('result')
    message_id = result.get('message_id') if isinstance(result, dict) else None
    return message_id if isinstance(message_id, int) else None


def _build_caption(title, summary, url, tags, max_length, why=''):
    # HTML вместо Markdown: html.escape() корректно экранирует весь текст
    # одной функцией, тогда как ручное экранирование '*_[]`' (как было раньше)
    # легко пропустить в одном из двух мест отправки и получить упавший запрос.
    # Хэштеги в конец поста, а не в начало: поиск Telegram смотрит весь текст,
    # а начало занимают заголовок и выжимка, которые видно в превью.
    prefix = f"<b>{html.escape(title)}</b>\n\n"
    # Ссылка «Читать полностью» — только если у поста есть одна статья (url).
    # Дайджест («Главное в мире за день») собирает несколько тем без единой
    # ссылки — для него url='' и суффикс ограничивается хэштегом категории.
    suffix = ''
    if url:
        suffix = f'\n\n<a href="{html.escape(url)}">Читать полностью</a>'
    if tags:
        suffix += '\n\n' + ' '.join(html.escape(tag) for tag in tags)

    # Редакторский блок «Почему это важно» — часть бюджета caption'а, но
    # уступает новости: если после него на выжимку остаётся меньше
    # MIN_SUMMARY_BUDGET символов, блок выбрасывается, а текст статьи остаётся.
    why_block = ''
    if why:
        why_block = f'\n\n<b>Почему это важно:</b> {html.escape(why)}'
    budget = max_length - len(prefix) - len(suffix) - len(why_block)
    if why_block and budget < MIN_SUMMARY_BUDGET:
        why_block = ''
        budget = max_length - len(prefix) - len(suffix)
    budget = max(0, budget)

    # Обрезаем только выжимку — и до экранирования. Раньше резали готовый HTML
    #     целиком: caption упирался в лимит 1024, и обрезка могла перерезать тег
    # `<a href="...` пополам — Telegram отвечал 400 "Unclosed start tag" и пост
    # уходил без фото. html.escape() удлиняет текст (например, `&` -> `&amp;`),
    # поэтому после обрезки проверяем реальную длину и ужимаем ещё раз.
    # max() защищает от отрицательного размера выжимки, если весь лимит уже
    # занят префиксом+суффиксом: слайс summary[:-N] обрезал бы хвост, а не
    # начало, и пост ушёл бы с битой выжимкой.
    summary = summary[:budget]
    while html.escape(summary) and len(html.escape(summary)) > budget:
        summary = summary[:-1]
    return prefix + html.escape(summary) + why_block + suffix


def post_news(chat_id, title, summary, url, image_bytes, category='',
              tags='', image_content_type='image/jpeg', why=''):
    """Публикует новость в канал и возвращает message_id поста (None, если
    отправить не удалось). Картинка отправляется байтами (multipart),
    а не ссылкой — Telegram принимает файл напрямую и не зависит от того,
    доступен ли внешний хост в момент публикации. Если Telegram не смог
    обработать фото — отправляем тот же текст без фото, чтобы не терять
    новость полностью."""
    hashtags = _normalize_tags(category, tags)
    if image_bytes:
        caption = _build_caption(title, summary, url, hashtags, max_length=1024,
                                 why=why)
        try:
            response = requests.post(
                f'{API_URL}/sendPhoto',
                data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'},
                files={'photo': ('news.jpg', image_bytes, image_content_type)},
                timeout=30,
            )
            response.raise_for_status()
            if not _ok(response):
                raise RuntimeError(f"Telegram вернул ok:false: {response.json().get('description')}")
            return _message_id(response)
        except Exception as e:
            logger.warning(f"Не удалось отправить фото ({e}), пробую текстом")

    text = _build_caption(title, summary, url, hashtags, max_length=4096, why=why)
    try:
        response = requests.post(
            f'{API_URL}/sendMessage',
            data={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
            timeout=30,
        )
        response.raise_for_status()
        if not _ok(response):
            raise RuntimeError(f"Telegram вернул ok:false: {response.json().get('description')}")
        return _message_id(response)
    except Exception as e:
        logger.error(f"Ошибка отправки в Telegram: {e}")
        return None


def post_poll(chat_id, question, options, reply_to_message_id=None):
    """Публикует опрос к посту и возвращает message_id опроса (None — не вышло).

    Опрос — украшение, а не часть новости: пост к этому моменту уже отправлен
    и статья уже помечена опубликованной, поэтому любые ошибки здесь только
    логируются. Падение опроса не имеет права выглядеть как упавшая публикация.

    Варианты уходят в Bot API JSON-строкой: обычный список в urlencoded-теле
    превращается в «options[]=...» и Telegram отвечает 400.
    В каналах опрос обязан быть анонимным — неанонимный канал не примет."""
    question = (question or '').strip()[:POLL_QUESTION_LIMIT]
    clean = []
    for option in options or []:
        option = str(option).strip()[:POLL_OPTION_LIMIT]
        if option and option not in clean:
            clean.append(option)
    clean = clean[:POLL_MAX_OPTIONS]
    if not question or len(clean) < POLL_MIN_OPTIONS:
        return None

    data = {
        'chat_id': chat_id,
        'question': question,
        'options': json.dumps(clean, ensure_ascii=False),
        'is_anonymous': True,
    }
    if reply_to_message_id:
        data['reply_to_message_id'] = reply_to_message_id
        # Пост мог быть удалён модератором/автором между отправкой и опросом:
        # без этого флага Telegram ответит 400 и опрос не выйдет вообще.
        data['allow_sending_without_reply'] = True

    try:
        response = requests.post(f'{API_URL}/sendPoll', data=data, timeout=30)
        response.raise_for_status()
        if not _ok(response):
            raise RuntimeError(f"Telegram вернул ok:false: {response.json().get('description')}")
        return _message_id(response)
    except Exception as e:
        logger.warning(f"Опрос не опубликован ({e}), пост остаётся без опроса")
        return None
