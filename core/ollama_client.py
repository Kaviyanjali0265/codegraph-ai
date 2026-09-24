from typing import Generator
import ollama

LLM_MODEL = "llama3.2:1b"
CLASSIFIER_MODEL = "llama3.2:3b"  # stronger model for classification only
EMBED_MODEL = "nomic-embed-text"


def embed(text: str) -> list[float]:
    response = ollama.embed(model=EMBED_MODEL, input=text)
    return response.embeddings[0]


def llm(prompt: str) -> str:
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.message.content


def llm_classify(prompt: str) -> str:
    """Uses the stronger 3b model for classification decisions only."""
    response = ollama.chat(
        model=CLASSIFIER_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.message.content


def llm_stream(prompt: str) -> Generator[str, None, None]:
    """Stream tokens from Ollama one by one as they are generated."""
    stream = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in stream:
        token = chunk.message.content
        if token:
            yield token
