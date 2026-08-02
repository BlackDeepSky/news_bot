from urllib.parse import quote

# Pollinations.ai — бесплатная генерация изображений без ключа и без карты:
# сама картинка рендерится по требованию, когда Telegram скачивает URL, так
# что нам не нужно ничего скачивать/загружать самим — просто отдаём ссылку
# в sendPhoto, как и обычную картинку из RSS. Если сервис недоступен или
# генерация не удалась — publisher.py уже умеет откатываться на текст без фото.
BASE_URL = 'https://image.pollinations.ai/prompt/'


def generate_image_url(title):
    prompt = f"digital illustration for a tech news article, no text, no watermark: {title}"
    return f"{BASE_URL}{quote(prompt)}?width=1024&height=576&nologo=true"
