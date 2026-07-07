import asyncio
import logging
from groq import AsyncGroq, RateLimitError, APIError, APIConnectionError, AuthenticationError
from application.ports.llm_port import LLMPort
from infrastructure.exceptions.infrastructure_exceptions import (
    LLMAdapterError,
    LLMRateLimitError,
    LLMEmptyResponseError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_BASE_BACKOFF_SECONDS = 2


class GroqLLMAdapter(LLMPort):
    """
    Concrete implementation of LLMPort that adapts the Groq async SDK.

    Responsibilities:
    - Translates application-level generate() calls into Groq chat completion requests.
    - Keeps all Groq SDK types (RateLimitError, APIError, etc.) strictly inside this module.
    - Raises only infrastructure exceptions — never domain exceptions.
    - Implements exponential-backoff retry on rate limits and transient 5xx errors.
    """

    def __init__(self, api_key: str, model: str) -> None:
        import httpx

        if not api_key or not api_key.strip():
            raise ConfigurationError(
                "GROQ_API_KEY is missing or empty. "
                "Ensure it is set in your .env file and loaded via environment configuration."
            )
        if not model or not model.strip():
            raise ConfigurationError("Groq model name must be a non-empty string.")

        # Instantiate a native httpx client to bypass the deprecated 'proxies' argument bug 
        # in groq 0.11.0's AsyncHttpxClientWrapper when used with httpx 0.28.0+
        http_client = httpx.AsyncClient()
        self._client = AsyncGroq(api_key=api_key, http_client=http_client)
        self._model = model
        logger.info("GroqLLMAdapter initialised | model=%s", self._model)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """
        Send a chat completion request to the Groq API.

        Retries up to _MAX_RETRIES times on:
        - Rate limit (429) responses — with exponential back-off.
        - Transient Groq server errors (5xx).

        Raises:
            LLMRateLimitError: If rate limit is exhausted after all retries.
            LLMEmptyResponseError: If the model returns a blank/null content field.
            LLMAdapterError: For all other non-retryable API failures.
        """
        if not system_prompt or not user_prompt:
            raise LLMAdapterError("Both system_prompt and user_prompt must be non-empty strings.")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        for attempt in range(_MAX_RETRIES + 1):
            try:
                logger.info(
                    "Groq request | model=%s | temp=%.1f | attempt=%d/%d",
                    self._model,
                    temperature,
                    attempt + 1,
                    _MAX_RETRIES + 1,
                )

                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                )

                # Validate response structure before returning
                choices = response.choices
                if not choices or len(choices) == 0:
                    raise LLMEmptyResponseError(
                        "Groq returned a response with no choices. "
                        f"Model: {self._model}"
                    )

                content = choices[0].message.content
                if not content or not content.strip():
                    raise LLMEmptyResponseError(
                        "Groq returned an empty or whitespace-only content field. "
                        f"Model: {self._model}"
                    )

                logger.info(
                    "Groq response received | model=%s | content_length=%d chars",
                    self._model,
                    len(content),
                )
                return content.strip()

            except LLMEmptyResponseError:
                # Empty response is non-retryable — surface immediately
                raise

            except RateLimitError as exc:
                if attempt < _MAX_RETRIES:
                    wait = _BASE_BACKOFF_SECONDS ** (attempt + 1)
                    logger.warning(
                        "Groq rate limit hit on attempt %d. Retrying in %ds...",
                        attempt + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        "Groq rate limit exhausted after %d retries.", _MAX_RETRIES
                    )
                    raise LLMRateLimitError(
                        f"Groq API rate limit exceeded after {_MAX_RETRIES} retries."
                    ) from exc

            except AuthenticationError as exc:
                # Authentication failures are never retryable
                logger.error("Groq authentication failed — check GROQ_API_KEY configuration.")
                raise ConfigurationError(
                    "Groq authentication failed. GROQ_API_KEY may be invalid or expired."
                ) from exc

            except APIConnectionError as exc:
                if attempt < _MAX_RETRIES:
                    wait = _BASE_BACKOFF_SECONDS ** (attempt + 1)
                    logger.warning(
                        "Groq connection error on attempt %d. Retrying in %ds...",
                        attempt + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("Groq connection failed after %d retries.", _MAX_RETRIES)
                    raise LLMAdapterError(
                        f"Connection to Groq API failed after {_MAX_RETRIES} retries."
                    ) from exc

            except APIError as exc:
                # Retry only on Groq 5xx server-side errors
                if attempt < _MAX_RETRIES and exc.status_code and exc.status_code >= 500:
                    wait = _BASE_BACKOFF_SECONDS ** (attempt + 1)
                    logger.warning(
                        "Groq server error %d on attempt %d. Retrying in %ds...",
                        exc.status_code,
                        attempt + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        "Groq API error (status=%s): %s",
                        exc.status_code,
                        exc.message,
                    )
                    raise LLMAdapterError(
                        f"Groq API error (HTTP {exc.status_code}): {exc.message}"
                    ) from exc

            except Exception as exc:
                # Catch-all for unexpected SDK internals — do not retry
                logger.error(
                    "Unexpected error during Groq API call: %s", str(exc), exc_info=True
                )
                raise LLMAdapterError(
                    f"Unexpected error during LLM generation: {type(exc).__name__}: {str(exc)}"
                ) from exc

        # Exhausted all retries without returning or raising — safety net
        raise LLMAdapterError(
            f"Groq LLM generation failed after {_MAX_RETRIES} retries with no response."
        )
