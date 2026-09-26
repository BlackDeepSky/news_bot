from loguru import logger

from config import OPENROUTER_API_KEY, OPENROUTER_MODELS
from retry import post_with_retry

# Общая точка входа в OpenRouter для всех трёх мест, которые бьют по LLM
# (ai.process_article, selector.select_best, digest.build_digest). Единый
# код перебора моделей появился после 26.09.2026, когда дайджест пропал из-за
# «HTTP 200 без choices»: раньше ответ вида {"error": {...}} без поля choices
# падал в KeyError 'choices', тело ошибки нигде не логировалось, и понять
# причину по логам было нельзя.
API_URL = 'https://openrouter.ai/api/v1/chat/completions'


def chat_completion(messages, *, temperature, max_tokens, task=''):
    """Ответ модели одним запросом; '' — если не ответила ни одна модель.

    Модели перебираются по OPENROUTER_MODELS: сначала основная, затем
    запасная. Переход к следующей происходит в двух случаях, оба — регулярные
    режимы отказа free-пулов OpenRouter:

    * провайдер положил ошибку в тело при HTTP 200 (нет поля choices) —
      логируем тело целиком, без этого причина сбоя невидима;
    * 429/5xx/сеть — post_with_retry делает три попытки с паузой, затем
      исключение, и мы пробуем следующую модель (не тот же самый пул).

    Пустая строка означает «не ответила ни одна модель»: вызывающий код
    пропускает статью, в канал мусор не уходит.
    """
    where = f" ({task})" if task else ''
    headers = {'Authorization': f'Bearer {OPENROUTER_API_KEY}'}

    for model in OPENROUTER_MODELS:
        payload = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            # Reasoning-модели тратят max_tokens на рассуждения вслух и не
            # успевают выдать ответ — глушим для всех моделей списка.
            'reasoning': {'enabled': False},
        }
        try:
            response = post_with_retry(API_URL, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            body = response.json()
        except Exception as e:
            logger.error(f"Ошибка запроса к OpenRouter{where} [{model}]: {e}")
            continue

        choices = body.get('choices') if isinstance(body, dict) else None
        if not choices:
            logger.error(
                f"OpenRouter вернул ответ без choices{where} [{model}]: {str(body)[:300]}")
            continue

        content = ((choices[0].get('message') or {}).get('content') or '').strip()
        if not content:
            logger.error(
                f"OpenRouter вернул пустой content{where} [{model}]: {str(body)[:300]}")
            continue

        # Успех. Если сработала не первая модель — это видно в логах выше
        # (ошибка по основной), здесь дублировать не нужно.
        return content

    return ''
