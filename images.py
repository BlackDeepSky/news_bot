import requests
from loguru import logger

from config import MAX_IMAGE_BYTES
from urlutils import is_safe_url


def download_image(url, timeout=90):
    """Скачивает картинку и возвращает (байты, content-type), если URL реально
    отдал изображение. Пустые байты/text not image — ошибка: так мы отсекаем
    битые ссылки и медленные сервисы раньше, чем их попробует Telegram."""
    if not url:
        return None

    # Анти-SSRF (лёгкий уровень): не качаем ничего из локальных/private-сетей,
    # даже если ссылку на них прислала внешняя лента. См. urlutils.is_safe_url.
    if not is_safe_url(url):
        logger.warning(f"Небезопасный URL картинки, пропускаю: {url}")
        return None

    try:
        # stream=True + iter_content: читаем по кускам и обрываем, как только
        # набралось больше MAX_IMAGE_BYTES — иначе response.content собрал бы
        # весь (возможно гигантский) файл в память до любой проверки.
        with requests.get(url, timeout=timeout, stream=True) as response:
            response.raise_for_status()
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"URL не отдал картинку {url}: content-type={content_type}")
                return None

            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > MAX_IMAGE_BYTES:
                    logger.warning(f"Картинка больше {MAX_IMAGE_BYTES} байт, пропускаю: {url}")
                    return None
                chunks.append(chunk)
            if not chunks:
                logger.warning(f"URL не отдал картинку {url}: пустые байты")
                return None
    except Exception as e:
        logger.warning(f"Не удалось скачать картинку {url}: {e}")
        return None

    return b''.join(chunks), content_type


def fetch_image(candidates, timeout=90):
    """Пробует кандидатов по очереди, возвращает (байты, выбранный_url)
    первой успешно скачанной картинки. None, если ни один кандидат не прошёл —
    вызывающий код пропустит статью, чтобы в канал не уходили посты без фото."""
    for url in candidates:
        result = download_image(url, timeout=timeout)
        if result:
            return result[0], url
    return None