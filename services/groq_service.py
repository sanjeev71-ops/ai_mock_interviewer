"""Isolated Groq provider.

The rest of the application never touches the OpenAI-compatible client
directly — it only calls GroqService.generate_json(), which guarantees
a validated dict (or raises). Structured-output validation, retries,
model failover, and schema checks live in one place.
"""

import json
import re
import time

from openai import OpenAI

from config.settings import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
)


# Free-tier chat models, most capable first.
FREE_CHAT_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]


class GroqService:
    def __init__(
        self,
        model: str | None = None,
        fallback_models: list[str] | None = None,
    ):
        self.client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url=GROQ_BASE_URL,
        )
        self.model = model or GROQ_MODEL
        self.fallback_models = (
            list(fallback_models)
            if fallback_models is not None
            else [
                candidate
                for candidate in FREE_CHAT_MODELS
                if candidate != self.model
            ]
        )
        # First model that succeeds is pinned for all
        # later calls on this instance (one interview
        # never mixes model styles).
        self.active_model: str | None = None

    @staticmethod
    def _extract_json(content: str) -> dict:
        """Parse model output robustly.

        Handles:
        - raw JSON
        - markdown-fenced JSON (```json ... ```)
        - trailing prose around the JSON object
        """
        text = content.strip()

        # Strip markdown code fences if present.
        fence_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL
        )
        if fence_match:
            text = fence_match.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fallback: extract the first {...} block.
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            return json.loads(brace_match.group(0))

        raise ValueError("No valid JSON object found in model output.")

    @staticmethod
    def _backoff_seconds(error: Exception, attempt: int) -> float:
        """429s are per-minute quotas: wait out the window.

        Anything else is transient: short exponential backoff.
        """
        text = str(error).lower()

        if "429" in text or "rate_limit" in text:
            return min(60, 15 * (attempt + 1))

        return 2**attempt

    @staticmethod
    def _is_request_too_large(error: Exception) -> bool:
        """Oversized requests can't be fixed by failover."""
        text = str(error).lower()
        return (
            "too large" in text or "reduce max_tokens" in text
        )

    def _chain(self) -> list[str]:
        ordered = []

        for candidate in [
            self.active_model,
            self.model,
            *self.fallback_models,
        ]:
            if candidate and candidate not in ordered:
                ordered.append(candidate)

        return ordered

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        retries: int = 3,
        max_tokens: int | None = None,
    ) -> dict:
        """Request a JSON object from the model.

        max_tokens caps the *requested* output size. Providers
        such as Groq reject oversized requests (HTTP 429 with
        "Request too large") before generation, so batched
        callers must keep this under the tier limit.

        On model-level failure the next model in the chain is
        tried; the first success pins the active model.
        """
        failures = []

        for model in self._chain():
            last_error = None

            for attempt in range(retries):
                try:
                    request = dict(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt,
                            },
                            {
                                "role": "user",
                                "content": user_prompt,
                            },
                        ],
                        temperature=0.3,
                        response_format={
                            "type": "json_object"
                        },
                    )

                    if max_tokens is not None:
                        request["max_tokens"] = max_tokens

                    response = (
                        self.client.chat.completions.create(
                            **request
                        )
                    )

                    content = response.choices[0].message.content

                    if not content:
                        raise ValueError(
                            "Groq returned an empty response."
                        )

                    data = self._extract_json(content)

                    if not isinstance(data, dict):
                        raise ValueError(
                            "Groq did not return a JSON object."
                        )

                    self.active_model = model

                    return data

                except Exception as error:
                    if self._is_request_too_large(error):
                        raise

                    last_error = error
                    if attempt < retries - 1:
                        time.sleep(
                            self._backoff_seconds(
                                error, attempt
                            )
                        )

            failures.append(f"{model}: {last_error}")

        raise RuntimeError(
            f"Groq API request failed after "
            f"{retries} attempts on every model "
            f"({'; '.join(failures)})"
        )
