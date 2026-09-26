import requests
from loguru import logger

from config import PEXELS_API_KEY

API_URL = 'https://api.pexels.com/v1/search'


def search_photo(query):
    """Ищет одно стоковое фото по ключевым словам. Пустая строка, если
    ничего не нашли или запрос не удался — вызывающий код просто идёт
    дальше по цепочке источников картинки."""
    if not query:
        return ''

    headers = {'Authorization': PEXELS_API_KEY}
    params = {'query': query, 'per_page': 1, 'orientation': 'landscape'}

    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        photos = response.json().get('photos', [])
        if not photos:
            return ''
        # large (940px) стабильно не проходил MIN_IMAGE_LONG_SIDE=1080 и просто
        # сжигал кандидата; large2x — 1880x1253, порог проходит. Остальные
        # ключи оставлены страховкой на случай изменения схемы API.
        src = photos[0].get('src', {})
        return src.get('large2x') or src.get('original') or src.get('large') or ''
    except Exception as e:
        logger.error(f"Ошибка запроса к Pexels: {e}")
        return ''
