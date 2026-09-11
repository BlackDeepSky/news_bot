import struct

import requests
from loguru import logger

from config import MAX_IMAGE_BYTES, MIN_IMAGE_LONG_SIDE
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


def _image_dimensions(data):
    """Возвращает (ширина, высота) по заголовку файла или None, если формат
    не распознан. Размеры JPEG/PNG/GIF читаются из магических байтов без
    Pillow; формат, который не умеем читать (WebP и т.п.), не отвергаем —
    None означает «не знаю, не мешаю»."""
    if data[:4] == b'\x89PNG' and len(data) >= 24:
        width, height = struct.unpack('>II', data[16:24])
        return width, height

    if data[:6] in (b'GIF87a', b'GIF89a') and len(data) >= 10:
        width, height = struct.unpack('<HH', data[6:10])
        return width, height

    if data[:2] == b'\xff\xd8':
        # JPEG: идём по маркерам и ищем кадр (SOF) — только там реальные
        # размеры. Каждый сегмент пролистываем по его длине, маркеры без
        # данных (RST/DNL/EOI) просто перешагиваем.
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker == 0xFF or 0xD0 <= marker <= 0xD9:
                i += 2
                continue
            seg_len = struct.unpack('>H', data[i + 2:i + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack('>HH', data[i + 5:i + 9])
                return width, height
            i += 2 + seg_len

    return None


def fetch_image(candidates, timeout=90):
    """Пробует кандидатов по очереди, возвращает (байты, выбранный_url)
    первой успешно скачанной картинки. None, если ни один кандидат не прошёл —
    вызывающий код пропустит статью, чтобы в канал не уходили посты без фото.
    Картинку мельче MIN_IMAGE_LONG_SIDE пропускаем: Telegram всё равно сожмёт
    фото до ~1280px, а маленький исходник превратится в размытый апскейл."""
    for url in candidates:
        result = download_image(url, timeout=timeout)
        if not result:
            continue
        image_bytes, _content_type = result
        width, height = _image_dimensions(image_bytes) or (0, 0)
        if 0 < max(width, height) < MIN_IMAGE_LONG_SIDE:
            logger.warning(f"Картинка слишком мала ({width}x{height}), пропускаю: {url}")
            continue
        return image_bytes, url
    return None