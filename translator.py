from transformers import pipeline
from loguru import logger

translator = None

def load_translation_model():
    """Инициализация модели перевода"""
    global translator
    try:
        translator = pipeline(
            "translation_en_to_ru",
            model="Helsinki-NLP/opus-mt-en-ru",
            framework="pt"
        )
        logger.info("Модель перевода загружена")
    except Exception as e:
        logger.error(f"Ошибка загрузки переводчика: {e}")
        raise

def translate_text(text):
    """Перевод короткого текста"""
    if not text or len(text) > 500:
        return text[:500]
    try:
        return translator(text, max_length=100)[0]['translation_text']
    except Exception as e:
        logger.error(f"Ошибка перевода: {e}")
        return text