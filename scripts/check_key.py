
"""Verify Gemini API key, chat model and embedding model."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sopassist.config import Settings


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3


def request_with_retry(client, method, url, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.request(method, url, **kwargs)

            if (
                response.status_code in RETRYABLE_STATUS_CODES
                and attempt < MAX_RETRIES
            ):
                wait = 2 ** attempt
                print(f"[retry] HTTP {response.status_code}; waiting {wait}s")
                time.sleep(wait)
                continue

            return response

        except httpx.HTTPError:
            if attempt == MAX_RETRIES:
                raise

            wait = 2 ** attempt
            print(f"[retry] Network error; waiting {wait}s")
            time.sleep(wait)

    raise RuntimeError("Maximum retries exceeded")


def show_response(label, response):
    print(
        f"[{label}] HTTP {response.status_code}: "
        f"{response.text[:500]}"
    )


def main():
    settings = Settings()

    base_url = settings.llm_base_url.rstrip("/")

    print("=" * 60)
    print("GEMINI API CONNECTION CHECK")
    print("=" * 60)

    print(f"Base URL       : {base_url}")
    print(f"Chat model     : {settings.llm_model}")
    print(f"Embedding model: {settings.embed_model}")

    if not settings.llm_api_key:
        print("\nERROR: LLM_API_KEY is missing.")
        return 1

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    results = {
        "models": False,
        "chat": False,
        "embedding": False,
    }

    try:
        with httpx.Client(timeout=60) as client:

            # 1. Available models
            print("\n[1/3] Checking available models...")

            response = request_with_retry(
                client,
                "GET",
                f"{base_url}/models",
                headers=headers,
            )

            available_models = []

            if response.status_code == 200:
                model_data = response.json().get("data", [])

                available_models = [
                    model.get("id", "").removeprefix("models/")
                    for model in model_data
                ]

                print("[models] OK")

                model_available = (
                    settings.llm_model.removeprefix("models/")
                    in available_models
                )

                print(
                    "Configured chat model available:",
                    model_available,
                )

                # Informational check: successful chat request is
                # the definitive proof that the model is usable.
                results["models"] = model_available

            else:
                show_response("models", response)

            # 2. Chat completion
            print("\n[2/3] Testing chat completion...")

            response = request_with_retry(
                client,
                "POST",
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": settings.llm_model,
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "user",
                            "content": "Reply with the single word OK.",
                        }
                    ],
                },
            )

            if response.status_code == 200:
                answer = (
                    response.json()["choices"][0]["message"]["content"]
                )

                print(f"[chat] OK: {answer[:100].strip()}")
                results["chat"] = True

            else:
                show_response("chat", response)

            # 3. Embeddings
            print("\n[3/3] Testing embedding model...")

            response = request_with_retry(
                client,
                "POST",
                f"{base_url}/embeddings",
                headers=headers,
                json={
                    "model": settings.embed_model,
                    "input": ["needle stick injury reporting"],
                },
            )

            if response.status_code == 200:
                embedding = response.json()["data"][0]["embedding"]

                print(
                    f"[embedding] OK: dimensions = {len(embedding)}"
                )

                results["embedding"] = True

            else:
                show_response("embedding", response)

    except (
        httpx.HTTPError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as error:

        print(f"\n[ERROR] {type(error).__name__}: {error}")
        return 1

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    for component, passed in results.items():
        print(
            f"{component.upper():15}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    if all(results.values()):
        print("\nSUCCESS: Gemini API is ready.")
        return 0

    print("\nWARNING: One or more checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
