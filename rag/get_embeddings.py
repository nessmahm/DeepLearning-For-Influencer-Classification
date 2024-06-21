from sentence_transformers import SentenceTransformer

# https://huggingface.co/thenlper/gte-large
embedding_model = SentenceTransformer("thenlper/gte-large")


def get_embedding(text: str) -> list[float]:
    if not text or not text.strip():
        print("Attempted to get embedding for empty text.")
        return []

    embedding = embedding_model.encode(text)

    return embedding.tolist()


