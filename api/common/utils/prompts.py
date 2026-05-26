import os
import functools

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@functools.lru_cache(maxsize=None)
def load_prompt(filename: str) -> str:
    prompt_path = os.path.join(BASE_DIR, 'prompts', filename)
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()
