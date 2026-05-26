import os
import functools
from django.conf import settings

@functools.lru_cache(maxsize=None)
def load_prompt(filename: str) -> str:
    prompt_path = os.path.join(settings.BASE_DIR, 'prompts', filename)
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()
