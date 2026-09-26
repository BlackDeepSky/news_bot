import html
import re

import trafilatura
from loguru import logger

from urlutils import is_safe_url

# Ограничение на входной текст для ИИ — экономит токены и держит запрос
# в пределах контекста бесплатной модели.
MAX_CHARS = 4000

# Изолируем сам <meta ...> тег, а не сразу content= — атрибуты в реальном
# HTML идут в разном порядке (то property перед content, то наоборот).
OG_IMAGE_TAG_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]*>', re.IGNORECASE
)
CONTENT_ATTR_RE = re.compile(r'content=["\']([^"\']+)["\']', re.IGNORECASE)


def _extract_og_image(html_text):
    tag_match = OG_IMAGE_TAG_RE.search(html_text)
    if not tag_match:
        return ''
    content_match = CONTENT_ATTR_RE.search(tag_match.group(0))
    if not content_match:
        return ''
    # В HTML амперсанды экранированы: href с "&amp;h=900" уходил в requests
    # как есть, и CDN отвечал 400 (поймано вживую на images.ctfassets.net
    # 26.09.2026). unescape возвращает URL к рабочему виду.
    return html.unescape(content_match.group(1))


def get_article(url):
    """Скачивает страницу один раз и возвращает (текст_статьи, og:image).
    RSS редко даёт картинку (проверено вживую на Habr, TechCrunch), а вот
    og:image на самой странице у них почти всегда есть — та же картинка,
    что видна в превью ссылки в мессенджерах. URL статьи приходит из внешнего
    фида — перед загрузкой проверяем, что он не ведёт в локальные/private
    сети (анти-SSRF, см. urlutils.is_safe_url)."""
    if not is_safe_url(url):
        logger.warning(f"Небезопасный URL статьи, пропускаю: {url}")
        return '', ''

    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return '', ''
        text = trafilatura.extract(downloaded) or ''
        image = _extract_og_image(downloaded)
        return text[:MAX_CHARS], image
    except Exception as e:
        logger.error(f"Ошибка извлечения статьи {url}: {e}")
        return '', ''
