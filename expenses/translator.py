from deep_translator import GoogleTranslator

def translate_text(text, source, target):
    text = (text or "").strip()
    if not text:
        return "", None

    try:
        translated = GoogleTranslator(source=source, target=target).translate(text)
        return translated, None
    except Exception:
        return None, "Translation Service Unavailable right now. Check your internet connection and try again."