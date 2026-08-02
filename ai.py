import re
import requests
from loguru import logger

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL

API_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Один запрос делает и перевод, и суммаризацию сразу — при дневном лимите
# бесплатных запросов на OpenRouter два отдельных вызова на статью съели бы
# бюджет вдвое быстрее. Модель сама решает, нужен ли перевод (для Habr — нет).
PROMPT = (
    "Ты — редактор технического Telegram-канала. Тебе дан заголовок и текст "
    "статьи (на русском или английском языке).\n"
    "Ответь строго в формате:\n"
    "Заголовок: <заголовок на русском, не длиннее 100 символов>\n"
    "Текст: <выжимка на русском, 3-5 предложений, только факты, без вводных "
    "фраз вроде «в статье говорится»>\n\n"
    "Если оригинал уже на русском — не переводи дословно, а сократи своими словами.\n\n"
    "Заголовок статьи: {title}\n\n"
    "Текст статьи:\n{text}"
)

RESPONSE_RE = re.compile(
    r'Заголовок:\s*(?P<title>.+?)\s*\n+\s*Текст:\s*(?P<summary>.+)',
    re.DOTALL,
)


def process_article(title, text):
    """Возвращает (заголовок_ru, выжимка_ru). При любой ошибке — ('', ''),
    чтобы вызывающий код просто пропустил статью, а не упал."""
    if not text:
        return '', ''

    payload = {
        'model': OPENROUTER_MODEL,
        'messages': [{'role': 'user', 'content': PROMPT.format(title=title, text=text)}],
        'temperature': 0.3,
        'max_tokens': 400,
    }
    headers = {'Authorization': f'Bearer {OPENROUTER_API_KEY}'}

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(f"Ошибка запроса к OpenRouter: {e}")
        return '', ''

    match = RESPONSE_RE.search(content)
    if not match:
        # Модель не выдержала формат — используем её ответ целиком как
        # выжимку, а заголовок оставляем оригинальным, лишь бы не терять статью.
        logger.warning("Ответ модели не в ожидаемом формате, использую как есть")
        return title, content

    return match.group('title').strip(), match.group('summary').strip()
