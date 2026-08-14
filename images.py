import requests
from loguru import logger


def download_image(url, timeout=90):
    """Скачивает картинку и возвращает (байты, content-type), если URL реально
    отдал изображение. Пустые байты/text not image — ошибка: так мы отсекаем
    битые ссылки и медленные сервисы раньше, чем их попробует Telegram."""
    if not url:
        return None

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except Exception as e:
        logger.warning(f"Не удалось скачать картинку {url}: {e}")
        return None

    content_type = response.headers.get('content-type', '')
    if not content_type.startswith('image/') or not response.content:
        logger.warning(f"URL не отдал картинку {url}: content-type={content_type}")
        return None

    return response.content, content_type


def fetch_image(candidates, timeout=90):
    """Пробует кандидатов по очереди, возвращает (байты, выбранный_url)
    первой успешно скачанной картинки. None, если ни один кандидат не прошёл —
    вызывающий код пропустит статью, чтобы в канал не уходили посты без фото."""
    for url in candidates:
        result = download_image(url, timeout=timeout)
        if result:
            return result[0], url
    return None