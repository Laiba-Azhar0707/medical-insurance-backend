import re


def strip_thinking_blocks(text):
    """
    Removes <think>...</think> reasoning traces that newer reasoning models
    sometimes include before their actual output. This must run before
    treating the text as final OCR output or before parsing it as JSON.
    """
    if not text:
        return text
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()