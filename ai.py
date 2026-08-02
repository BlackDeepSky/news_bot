import re
import requests
from loguru import logger

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL

API_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Один запрос делает и перевод, и суммаризацию сразу — при дневном лимите
# бесплатных запросов на OpenRouter два отдельных вызова на статью съели бы
# бюджет вдвое быстрее. Модель сама решает, нужен ли перевод (для Habr — нет).
#
# Системный промпт с требованием "только русский" вынесен отдельно и
# продублирован в пользовательском — на реальных прогонах модель (особенно
# MoE вроде nemotron) иногда оставляла отдельные слова/фразы непереведёнными
# ("exposing PII", "bipartisan") или роняла случайный иероглиф — одного
# упоминания в промпте оказалось недостаточно.
SYSTEM_PROMPT = (
    "Ты — редактор технического Telegram-канала. Отвечай ТОЛЬКО на русском "
    "языке: каждое слово должно быть русским. Переводи вообще всё, включая "
    "термины и фразы вроде 'bipartisan' или 'exposing PII' — не оставляй их "
    "на английском или любом другом языке. Названия продуктов, компаний и "
    "брендов (ChatGPT, GitHub, Boston Dynamics) можно оставлять как есть."
)

PROMPT = (
    "Тебе дан заголовок и текст статьи (на русском или английском языке).\n"
    "Ответь строго в формате:\n"
    "Заголовок: <заголовок на русском, не длиннее 100 символов>\n"
    "Текст: <выжимка на русском, 3-5 предложений, только факты, без вводных "
    "фраз вроде «в статье говорится»>\n\n"
    "Если оригинал уже на русском — не переводи дословно, а сократи своими словами.\n"
    "Напоминание: ответ целиком должен быть на русском языке, без единого "
    "слова на английском или другом языке (кроме имён собственных).\n\n"
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
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': PROMPT.format(title=title, text=text)},
        ],
        'temperature': 0.3,
        'max_tokens': 400,
        # Часть бесплатных моделей — reasoning-модели: без этого флага они
        # тратят весь max_tokens на рассуждения вслух и обрезаются раньше,
        # чем успевают выдать сам ответ (поймали вживую: content содержал
        # заглушку из промпта и оборванное рассуждение вместо результата).
        'reasoning': {'enabled': False},
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
        # Раньше здесь публиковался content как есть "лишь бы не терять
        # статью" — но вживую это пропустило в канал деградировавший ответ
        # модели (повторяющиеся <unk> и мусорные токены). Пропуск статьи —
        # намного дешевле, чем мусор в публичном канале.
        logger.warning(f"Ответ модели не в ожидаемом формате, пропускаю статью: {content[:200]!r}")
        return '', ''

    return match.group('title').strip(), match.group('summary').strip()
