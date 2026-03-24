import json
import requests
from app.config import config
import logging
_log = logging.getLogger(__name__)

def is_ollama_available() -> bool:
    try:
        r = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False

def chat(messages: list[dict], system: str = "", stream: bool = False, temperature: float = 0.7) -> str:
    payload = {"model": config.OLLAMA_CHAT_MODEL, "messages": messages, "stream": False, "options": {"temperature": temperature}}
    if system:
        payload["messages"] = [{"role": "system", "content": system}] + messages
    try:
        r = requests.post(f"{config.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")

def get_embedding(text: str) -> list[float]:
    try:
        r = requests.post(f"{config.OLLAMA_BASE_URL}/api/embeddings", json={"model": config.OLLAMA_EMBED_MODEL, "prompt": text}, timeout=30)
        r.raise_for_status()
        return r.json()["embedding"]
    except Exception as e:
        raise RuntimeError(f"Embedding error: {e}")
