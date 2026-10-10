"""Test script for running TypeSafe AI decision models (e.g. tev1:0.8b)
using `typesafe-sdk` connected to local Ollama.

System One decision models provide fast, calibrated, structured decision-making
(classification, scoring, routing, and guardrails) without conversational text generation.

Configuration:
    - Base URL: http://localhost:11434 (default Ollama endpoint)
    - API Key:  ollama (placeholder required by SDK)
    - Model:    tev1:0.8b (or any installed System One model)
"""

import asyncio
import os
import sys
from pathlib import Path
import httpx2
from pydantic import BaseModel

from typesafe_sdk import (
    AsyncTypeSafeClient,
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Score,
    ScoreAnswer,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeClient,
)


def load_env_file():
    """Load variables from .env file in project root if present."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("\"'")
                    if key and key not in os.environ:
                        os.environ[key] = val


def check_ollama_status(base_url: str, model_name: str):
    """Check if Ollama server is up and verify if the requested model is downloaded."""
    try:
        res = httpx2.get(f"{base_url.rstrip('/')}/api/tags", timeout=3.0)
        if res.status_code == 200:
            models_data = res.json().get("models", [])
            installed = [m.get("name") for m in models_data]
            print(f"[OK] Ollama is running at {base_url}")
            print(f"     Installed models: {installed if installed else 'None yet'}")
            
            matched = any(m == model_name or m.startswith(model_name.split(":")[0]) for m in installed)
            if not matched:
                print(f"[NOTE] '{model_name}' was not detected in `ollama list`.")
                print(f"       If you are still pulling it, run: `ollama pull {model_name}`")
            else:
                print(f"[OK] Found model '{model_name}' in Ollama.")
            return True
    except Exception as e:
        print(f"[WARNING] Could not connect to Ollama at {base_url}: {e}")
        print("          Ensure Ollama is running (`ollama serve`).")
        return False


def run_sync_evaluation(client: TypeSafeClient, model_name: str):
    print("\n" + "=" * 60)
    print(f"Running Synchronous System One Evaluation (Model: {model_name})")
    print("=" * 60)

    state = {
        "message": "I was double charged for my monthly subscription! Please refund the duplicate $50 immediately.",
        "user_tier": "enterprise",
    }
    print(f"Input State:\n  {state}\n")

    questions = {
        "is_urgent": Noul(
            instructions="Does the customer communicate urgent time sensitivity or distress?"
        ),
        "requests_refund": Noul(
            instructions="Is the user explicitly asking for a financial refund or credit?"
        ),
        "category": Choice(
            instructions="What is the primary department category for this request?",
            criteria={
                "billing": "Invoices, duplicate payments, refunds, payment method issues",
                "technical_support": "Software bugs, crashes, integrations, API errors",
                "general_inquiry": "Feature requests, documentation, product questions",
            },
        ),
        "severity": Score(
            instructions="Rate the urgency level of this customer ticket.",
            criteria=[
                "Low: General question, no time pressure",
                "Medium: Action needed within 2-3 business days",
                "High: Immediate action needed, financial impact or blocking issue",
            ],
        ),
    }

    print("Evaluating decision questions via System One endpoint...")
    result: SystemOneResponse = client.system_one(
        state=state,
        questions=questions,
        model=model_name,
    )

    print("\nResults:")
    for name, noul_ans in result.nouls.items():
        print(f"  [Noul]   {name:15}: Probability = {noul_ans.noul:.2%} (True: {noul_ans.noul > 0.5})")

    for name, choice_ans in result.choices.items():
        print(f"  [Choice] {name:15}: Selected = '{choice_ans.choice}' (Confidence: {choice_ans.confidence})")

    for name, score_ans in result.scores.items():
        print(f"  [Score]  {name:15}: Score = {score_ans.score} (Confidence: {score_ans.confidence})")

    if result.usage:
        print(f"\nToken Usage: Input={result.usage.input_tokens}, Output={result.usage.output_tokens}")


async def run_async_evaluation(base_url: str, api_key: str, model_name: str):
    print("\n" + "=" * 60)
    print(f"Running Asynchronous System One Evaluation (Model: {model_name})")
    print("=" * 60)

    state = {
        "message": "Where can I find documentation on configuring webhook secrets?",
        "user_tier": "free",
    }
    print(f"Input State:\n  {state}\n")

    questions = {
        "is_urgent": Noul(instructions="Does this request require immediate escalation?"),
        "category": Choice(
            instructions="Select ticket department.",
            criteria={
                "billing": "Billing and payment issues",
                "docs": "Documentation, guides, how-to tutorials",
                "bugs": "Production bugs and service downtime",
            },
        ),
    }

    async with AsyncTypeSafeClient(base_url=base_url, api_key=api_key, model=model_name) as client:
        print("Sending async evaluation request...")
        result = await client.system_one(state=state, questions=questions)
        print("\nAsync Results:")
        for name, ans in result.answers.items():
            if isinstance(ans, NoulAnswer):
                print(f"  {name}: {ans.noul:.2%}")
            elif isinstance(ans, ChoiceAnswer):
                print(f"  {name}: {ans.choice} (Confidence: {ans.confidence})")


def main():
    load_env_file()

    base_url = os.environ.get("TYPESAFE_BASE_URL", "http://localhost:11434")
    api_key = os.environ.get("TYPESAFE_API_KEY", "ollama")
    model_name = os.environ.get("TYPESAFE_DEFAULT_MODEL", "tev1:0.8b")

    print("=" * 60)
    print("TypeSafe SDK + Ollama Decision Model Test")
    print("=" * 60)
    print(f"Base URL : {base_url}")
    print(f"Model    : {model_name}")
    print(f"API Key  : {api_key}")
    print("-" * 60)

    check_ollama_status(base_url, model_name)

    client = TypeSafeClient(
        base_url=base_url,
        api_key=api_key,
        model=model_name,
    )

    try:
        run_sync_evaluation(client, model_name)
        asyncio.run(run_async_evaluation(base_url, api_key, model_name))
        print("\n[SUCCESS] All evaluation tests completed successfully!")
    except TypeSafeAPIConnectionError as e:
        print(f"\n[Connection Error]: Could not connect to {base_url}.")
        print("Please verify that Ollama is running (`ollama serve`) and accessible.")
    except TypeSafeAPIError as e:
        print(f"\n[API Error {e.status_code}]: {e.message}")
        if "model" in str(e).lower() or e.status_code == 404:
            print(f"Hint: Make sure the model '{model_name}' has finished installing:")
            print(f"      ollama pull {model_name}")
    except Exception as e:
        print(f"\n[Unexpected Error]: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
