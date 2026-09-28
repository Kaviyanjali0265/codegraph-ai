from typing import Generator
import ollama
from dotenv import load_dotenv
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

load_dotenv()

LLM_MODEL = "llama3.2:1b"
CLASSIFIER_MODEL = "llama3.2:3b"  # stronger model for classification only
EMBED_MODEL = "nomic-embed-text"


def embed(text: str) -> list[float]:
    response = ollama.embed(model=EMBED_MODEL, input=text)
    return response.embeddings[0]


def _record_token_usage(response) -> None:
    run = get_current_run_tree()
    if run is None:
        return
    input_tokens = response.prompt_eval_count or 0
    output_tokens = response.eval_count or 0
    run.metadata["usage_metadata"] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


@traceable(name="ollama_llm", run_type="llm")
def llm(prompt: str) -> str:
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    _record_token_usage(response)
    return response.message.content


@traceable(name="ollama_llm_classify", run_type="llm")
def llm_classify(prompt: str) -> str:
    """Uses the stronger 3b model for classification decisions only."""
    response = ollama.chat(
        model=CLASSIFIER_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    _record_token_usage(response)
    return response.message.content


@traceable(name="ollama_llm_stream", run_type="llm")
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
