import time

import requests


def post_with_retry(url, *, retries=3, backoff=2.0, **kwargs):
    """POST с экспоненциальной паузой на временные сбои (429, 5xx, сеть).

    OpenRouter/Pexels на бесплатных тирах регулярно отдают 429 — раньше такой
    ответ молча ронял статью насовсем. Здесь повторяем запрос с нарастающей
    паузой (2с -> 4с -> 8с). Ошибки 4xx, кроме 429, не ретраим — это уже
    ошибка в самом запросе, повторять бесполезно.
    """
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.post(url, **kwargs)
        except Exception as e:  # сеть/таймаут — временно, ретраим
            last_error = e
        else:
            if response.status_code in (429,) or response.status_code >= 500:
                last_error = requests.HTTPError(
                    f"HTTP {response.status_code} от {url}", response=response)
            else:
                return response

        if attempt == retries - 1:
            break
        time.sleep(backoff * (2 ** attempt))

    raise last_error
