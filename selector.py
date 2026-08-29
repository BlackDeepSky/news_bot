import random
import re
import requests
from loguru import logger

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL

API_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Просим вернуть только номер выбранного кандидата. free-модель (nemotron/MoE)
# склонна рассуждать вслух и портить формат — те же грабли, что и в ai.py.
SELECTOR_SYSTEM_PROMPT = (
    "Ты — редактор технического Telegram-канала. Из списка статей выбери "
    "одну, самую интересную и релевантную подписчикам. Оценивай по: "
    "новизне, практической пользе и неожиданности. Верни ТОЛЬКО номер "
    "выбранной статьи — одну цифру, без объяснений."
)

SELECTOR_PROMPT = (
    "Ниже список статей с номером, заголовком и кратким описанием:\n\n"
    "{list}\n\n"
    "Напиши номер самой интересной статьи. Только номер, одним числом, "
    "никакого текста вокруг."
)

def _build_candidate_list(candidates):
    """Собирает текст списка для промпта из (url, title, snippet)."""
    lines = []
    for i, (url, title, snippet) in enumerate(candidates, start=1):
        snippet = re.sub(r'\s+', ' ', (snippet or '')).strip()
        lines.append(f"{i}. {title} — {snippet}")
    return '\n'.join(lines)


def select_best(candidates):
    """Возвращает url самого интересного кандидата из списка
    (url, title, snippet). При любой ошибке — '', чтобы вызывающий код просто
    пропустил отбор и пошёл обычным путём."""
    if not candidates:
        return ''

    # Случайный порядок, чтобы модель не систематически тяготела к первому
    # пункту списка (нестабильность free-модели).
    shuffled = list(candidates)
    random.shuffle(shuffled)

    payload = {
        'model': OPENROUTER_MODEL,
        'messages': [
            {'role': 'system', 'content': SELECTOR_SYSTEM_PROMPT},
            {'role': 'user', 'content': SELECTOR_PROMPT.format(
                list=_build_candidate_list(shuffled))},
        ],
        'temperature': 0.3,
        'max_tokens': 100,
        # Reasoning-модели тратят max_tokens на рассуждения вслух и успевают
        # выдать пустоту — это уже поймано в ai.py, глушим здесь то же самое.
        'reasoning': {'enabled': False},
    }
    headers = {'Authorization': f'Bearer {OPENROUTER_API_KEY}'}

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(f"Ошибка запроса к OpenRouter при выборе статьи: {e}")
        return ''

    match = re.search(r'\d+', content)
    if not match:
        logger.warning(f"Модель не вернула номер при выборе статьи: {content[:200]!r}")
        return ''

    index = int(match.group())
    if not 1 <= index <= len(shuffled):
        logger.warning(f"Модель вернула номер вне диапазона ({index}), пропускаю отбор")
        return ''

    return shuffled[index - 1][0]
