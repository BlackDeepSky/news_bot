from urllib.parse import quote

# Pollinations.ai — бесплатная генерация изображений без ключа и без карты:
# сама картинка рендерится по требованию, когда Telegram скачивает URL, так
# что нам не нужно ничего скачивать/загружать самим — просто отдаём ссылку
# в sendPhoto, как и обычную картинку из RSS. Если сервис недоступен или
# генерация не удалась — publisher.py уже умеет откатываться на текст без фото.
#
# Анонимный Pollinations отдаёт максимум 1024x576 и игнорирует больший
# запрос (проверено 26.09.2026: на width=1280 пришло ровно 1024x576), поэтому
# и просим его максимум: отбраковку по MIN_IMAGE_LONG_SIDE=1080 прикрывает
# LAST_RESORT_LONG_SIDE в images.fetch_image.
BASE_URL = 'https://image.pollinations.ai/prompt/'


def generate_image_url(image_prompt):
    # image_prompt — короткое английское визуальное описание, которое уже
    # сгенерировал ai.py вместе с заголовком/выжимкой. Раньше сюда уходил
    # русский заголовок статьи целиком — на живых прогонах давало бессвязные
    # абстрактные картинки (Pollinations/Flux слабо понимает кириллицу),
    # не связанные по смыслу со статьёй.
    if not image_prompt:
        image_prompt = "abstract technology background, circuits and data, blue tones"
    prompt = f"digital illustration for a tech news article, no text, no watermark: {image_prompt}"
    return f"{BASE_URL}{quote(prompt)}?width=1024&height=576&nologo=true"
