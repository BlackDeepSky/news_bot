import ipaddress
import socket
import urllib.parse
from functools import lru_cache

from loguru import logger

# Утилиты для работы с URL вне сетевого слоя: нормализация для дедупликации
# (database.py) и проверка безопасности адреса (анти-SSRF, images.py /
# extractor.py). Выделено в отдельный модуль, чтобы одна логика жила в одном
# месте и её было легко покрыть тестами без сети.

# Только http/https: остальные схемы (file://, dict://, data:) бот не должен
# ни качать, ни считать «той же статьёй».
HTTP_SCHEMES = ('http', 'https')

# Параметры отслеживания, которые не меняют адрес самой статьи: один и тот же
# пост из RSS с utm/* и без них — это одна новость, а не две.
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'utm_id', 'fbclid', 'gclid', 'yclid', 'mc_cid', 'mc_eid', 'ref',
    'ref_src', 'spm',
}

# Сети, в которые бот не должен ходить: loopback, private, link-local
# (метаданные облаков 169.254.x.x, локальные сервисы на 127.0.0.1 и т.п.).
_PRIVATE_NETS = [
    ipaddress.ip_network(n)
    for n in ['127.0.0.0/8', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
              '169.254.0.0/16', '::1/128', 'fc00::/7', 'fe80::/10', '::ffff:127.0.0.0/104']
]


def normalize_url(url):
    """Каноническая форма URL для дедупликации: тот же адрес с разными
    служебными хвостами (utm, фрагмент, регистр/порт) — один ключ. Не-http
    адреса и мусор возвращаем как есть, чтобы дедуп их не ломал."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return url

    if parts.scheme.lower() not in HTTP_SCHEMES:
        return url

    host = (parts.hostname or '').lower()
    if not host:
        return url

    # Порт сохраняем, только если он нестандартный для схемы: example.com:443
    # и example.com — один адрес. Битый порт — отдаём как есть.
    try:
        port = parts.port
    except ValueError:
        return url
    default_port = 443 if parts.scheme == 'https' else 80
    if port and port == default_port:
        port = None
    netloc = host if port is None else f'{host}:{port}'

    # Убираем параметры отслеживания, сохраняя прочие (у CMS вида
    # /article?id=123 путь одинаковый, а различает именно query).
    keep = [
        q for q in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if q[0].lower() not in TRACKING_PARAMS
    ]
    new_query = urllib.parse.urlencode(keep)
    return urllib.parse.urlunsplit((parts.scheme.lower(), netloc, parts.path, new_query, ''))


@lru_cache(maxsize=256)
def _resolves_to_private(hostname):
    """True, если DNS-резолв хоста попадает хотя бы в одну закрытую сеть.
    Кэш по хосту: на один пост цепочка картинок проверяет несколько URL с
    одним CDN-хостом, резолвить каждый раз — лишняя сеть."""
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError as e:
        logger.warning(f"Не удалось разрешить {hostname}, считаю небезопасным: {e}")
        return True
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if any(ip in net for net in _PRIVATE_NETS):
            return True
    return False


def is_safe_url(url):
    """True, если по адресу можно ходить: схема http(s) и хост не указывает
    на локальные/private-сети (анти-SSRF). Проверяется только первый адрес —
    редиректы здесь не перехватываем (лёгкий уровень защиты, см. ревью)."""
    if not url:
        return False

    parts = urllib.parse.urlsplit(url)
    if parts.scheme.lower() not in HTTP_SCHEMES:
        return False

    host = (parts.hostname or '').strip()
    if not host:
        return False

    # Хост уже IP — проверяем напрямую; иначе резолвим и проверяем адреса.
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return not _resolves_to_private(host)

    return not any(ip in net for net in _PRIVATE_NETS)