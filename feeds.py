import feedparser
from loguru import logger


def get_entries(feed_url, limit):
    """Забирает последние записи RSS-ленты. При ошибке — пустой список,
    чтобы одна упавшая лента не останавливала обработку остальных."""
    try:
        parsed = feedparser.parse(feed_url)
    except Exception as e:
        logger.error(f"Не удалось загрузить ленту {feed_url}: {e}")
        return []

    if parsed.bozo and not parsed.entries:
        logger.warning(f"Лента повреждена или недоступна {feed_url}: {parsed.get('bozo_exception')}")
        return []

    return parsed.entries[:limit]


def entry_image(entry):
    """Достаёт URL картинки из записи — разные ленты кладут её в разные поля."""
    media_content = entry.get('media_content')
    if media_content:
        url = media_content[0].get('url')
        if url:
            return url

    media_thumbnail = entry.get('media_thumbnail')
    if media_thumbnail:
        url = media_thumbnail[0].get('url')
        if url:
            return url

    for link in entry.get('links', []):
        if link.get('type', '').startswith('image/'):
            return link.get('url', '')

    return ''
