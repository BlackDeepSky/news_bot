import trafilatura
from loguru import logger

# Ограничение на входной текст для ИИ — экономит токены и держит запрос
# в пределах контекста бесплатной модели.
MAX_CHARS = 4000


def get_article_text(url):
    """Скачивает страницу и вытаскивает основной текст статьи."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ''
        text = trafilatura.extract(downloaded) or ''
        return text[:MAX_CHARS]
    except Exception as e:
        logger.error(f"Ошибка извлечения текста {url}: {e}")
        return ''
