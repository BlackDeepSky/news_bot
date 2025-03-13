from googletrans import Translator

translator = Translator()

def translate_text(text, dest='ru'):
    """Перевод текста на русский"""
    if text:
        try:
            return translator.translate(text, dest=dest).text
        except Exception:
            return text  # Возвращаем оригинал, если перевод не удался
    return ''