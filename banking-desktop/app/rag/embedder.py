from app.llm.ollama_client import get_embedding

def embed_chunks(chunks: list[str]) -> list[tuple[str, list[float]]]:
    result = []
    for chunk in chunks:
        try:
            embedding = get_embedding(chunk)
            result.append((chunk, embedding))
        except Exception:
            result.append((chunk, []))
    return result
