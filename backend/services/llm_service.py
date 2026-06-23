from abc import ABC, abstractmethod
from collections.abc import Iterator

from google import genai
from google.genai import errors, types
from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.errors import NonRetryableError, RetryableError

GEMINI_GENERATION_MODEL = "gemini-3.1-flash-lite"  # "gemini-3.5-flash" OR "gemini-3.1-flash-lite"
OPENAI_GENERATION_MODEL = "gpt-4o-mini"
TIMEOUT_SECONDS = 90
MAX_RETRIES = 3


class LLMService(ABC):
    """Abstract interface for any LLM generation provider."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send a fully-assembled prompt and return the generated text."""

    @abstractmethod
    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Send a prompt and yield the generated text in fragments as they arrive."""


# ---------------------------------------------------------------------------
# Gemini implementation
# ---------------------------------------------------------------------------

class GeminiLLMService(LLMService):
    """Gemini generation with automatic retry/backoff on transient errors."""

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    @retry(
        retry=retry_if_exception_type(RetryableError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(MAX_RETRIES),
        reraise=True,
    )
    def generate(self, prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=GEMINI_GENERATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
            )
            return response.text
        except errors.APIError as e:
            if e.code in (429, 500, 503):
                raise RetryableError(f"Retryable API error ({e.code}): {e.message}") from e
            raise NonRetryableError(f"Non-retryable API error ({e.code}): {e.message}") from e
        except Exception as e:
            raise NonRetryableError(f"Unexpected error: {e}") from e

    def generate_stream(self, prompt: str) -> Iterator[str]:
        try:
            stream = self._client.models.generate_content_stream(
                model=GEMINI_GENERATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except errors.APIError as e:
            if e.code in (429, 500, 503):
                raise RetryableError(f"Retryable API error ({e.code}): {e.message}") from e
            raise NonRetryableError(f"Non-retryable API error ({e.code}): {e.message}") from e
        except Exception as e:
            raise NonRetryableError(f"Unexpected error: {e}") from e


# ---------------------------------------------------------------------------
# OpenAI implementation
# ---------------------------------------------------------------------------

class OpenAILLMService(LLMService):
    """OpenAI GPT implementation — same interface, different provider.

    Not used in production for this project (costs money / requires credit card).
    Demonstrates that the LLMService abstraction makes provider-swapping trivial.
    """

    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=OPENAI_GENERATION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=TIMEOUT_SECONDS,
        )
        return response.choices[0].message.content

    def generate_stream(self, prompt: str) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=OPENAI_GENERATION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=TIMEOUT_SECONDS,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
