import json
from anthropic import Anthropic
from google import genai as google_genai
from google.genai import types as google_types
from app.core.config import ZAI_API_KEY, GEMINI_API_KEY

_DEFAULT_PROVIDER     = "gemini"
_DEFAULT_GEMINI_KEY   = GEMINI_API_KEY
_DEFAULT_GEMINI_MODEL = "models/gemini-2.5-flash"

# Kept for agents that still have ilmu configured
_DEFAULT_ILMU_KEY   = ZAI_API_KEY
_DEFAULT_ILMU_MODEL = "ilmu-glm-5.1"

_ANTHROPIC_BASE_URLS: dict[str, str] = {
    "ilmu": "https://api.ilmu.ai/anthropic",
}


# ── SDK clients ───────────────────────────────────────────────────────────────

def _anthropic_client(api_key: str = None, model_provider: str = None) -> Anthropic:
    base_url = _ANTHROPIC_BASE_URLS.get(model_provider or "ilmu")
    return Anthropic(api_key=api_key or _DEFAULT_ILMU_KEY, base_url=base_url, timeout=25.0)


# ── Gemini helpers ────────────────────────────────────────────────────────────

def _to_gemini_history(messages: list) -> tuple[list, str]:
    history = [
        {
            "role":  "user" if m["role"] == "user" else "model",
            "parts": [m["content"]],
        }
        for m in messages[:-1]
    ]
    last_message = messages[-1]["content"] if messages else ""
    return history, last_message


def _call_gemini_session(
    api_key: str, model_name: str, system: str,
    messages: list, max_tokens: int, temperature: float, top_p: float,
) -> tuple[str, int]:
    client = google_genai.Client(api_key=api_key)
    history, last_message = _to_gemini_history(messages)

    contents = [
        google_types.Content(role=m["role"], parts=[google_types.Part(text=m["parts"][0])])
        for m in history
    ]
    contents.append(google_types.Content(role="user", parts=[google_types.Part(text=last_message)]))

    response = client.models.generate_content(
        model=model_name or _DEFAULT_GEMINI_MODEL,
        contents=contents,
        config=google_types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        ),
    )
    try:
        tokens = response.usage_metadata.total_token_count or 0
    except Exception:
        tokens = 0
    return response.text, tokens


# ── Public interface ──────────────────────────────────────────────────────────

def call_glm(
    max_tokens, requirements, context, temperature, top_p,
    prev_messages=None, previous_output=None,
    api_key: str = None, model_name: str = None, model_provider: str = None,
) -> str:
    """One-shot call. Returns reply text only (no user context for token tracking)."""
    provider    = model_provider or _DEFAULT_PROVIDER
    temperature = float(temperature) if temperature is not None else 0.7
    top_p       = float(top_p) if top_p is not None else 0.9
    max_tokens  = int(max_tokens) if max_tokens is not None else 1000

    if isinstance(context, dict):
        task     = context.get("task", "")
        business = context.get("business", {})
        context_str = (
            f"Task: {task}\n\n"
            f"Business Profile:\n"
            f"- Name: {business.get('name')}\n"
            f"- Type: {business.get('business_type')}\n"
            f"- Mode: {business.get('mode_of_business', 'n/a')}\n"
            f"- Expected Costs: {business.get('expected_costs')}\n"
            f"- Description: {business.get('brief_description')}\n\n"
            f"Provide a detailed analysis based on the above."
        )
    else:
        context_str = str(context)

    if prev_messages is None:
        messages = [{"role": "user", "content": context_str}]
    else:
        prev_str     = json.dumps(prev_messages)   if isinstance(prev_messages,   dict) else prev_messages
        prev_out_str = json.dumps(previous_output) if isinstance(previous_output, dict) else previous_output
        messages = [
            {"role": "user",      "content": prev_str},
            {"role": "assistant", "content": prev_out_str},
            {"role": "user",      "content": context_str},
        ]

    if provider == "gemini":
        text, _ = _call_gemini_session(
            api_key or _DEFAULT_GEMINI_KEY, model_name or _DEFAULT_GEMINI_MODEL,
            requirements, messages, max_tokens, temperature, top_p,
        )
        return text

    response = _anthropic_client(api_key, provider).messages.create(
        model=model_name or _DEFAULT_ILMU_MODEL,
        max_tokens=max_tokens, system=requirements,
        messages=messages, temperature=temperature, top_p=top_p,
    )
    return response.content[0].text


def call_glm_session(
    max_tokens, requirements, messages: list, temperature, top_p,
    api_key: str = None, model_name: str = None, model_provider: str = None,
) -> tuple[str, int]:
    """
    Multi-turn chat. Returns (reply_text, tokens_used).
    Tokens are actual input+output counts from the API for accurate billing.
    """
    provider    = model_provider or _DEFAULT_PROVIDER
    temperature = float(temperature) if temperature is not None else 0.7
    top_p       = float(top_p) if top_p is not None else 0.9
    max_tokens  = int(max_tokens) if max_tokens is not None else 1000

    if provider == "gemini":
        return _call_gemini_session(
            api_key or _DEFAULT_GEMINI_KEY,
            model_name or _DEFAULT_GEMINI_MODEL,
            requirements, messages, max_tokens, temperature, top_p,
        )

    response = _anthropic_client(api_key, provider).messages.create(
        model=model_name or _DEFAULT_ILMU_MODEL,
        max_tokens=max_tokens, system=requirements,
        messages=messages, temperature=temperature, top_p=top_p,
    )
    try:
        tokens = response.usage.input_tokens + response.usage.output_tokens
    except Exception:
        tokens = 0
    return response.content[0].text, tokens
