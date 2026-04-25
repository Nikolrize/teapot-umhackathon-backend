import json
from anthropic import Anthropic
from google import genai as google_genai
from google.genai import types as google_types
from app.core.config import ZAI_API_KEY

_DEFAULT_API_KEY  = ZAI_API_KEY
_DEFAULT_MODEL    = "ilmu-glm-5.1"
_DEFAULT_GEMINI_MODEL = "models/gemini-2.5-flash"
_DEFAULT_PROVIDER = "ilmu"

# Developer-maintained: Anthropic-SDK-compatible providers and their base URLs.
# Gemini is handled separately via its own SDK — no entry needed here.
# Add a new entry when onboarding a new Anthropic-compatible provider.
_ANTHROPIC_BASE_URLS: dict[str, str] = {
    "ilmu": "https://api.ilmu.ai/anthropic",
}


# ── SDK clients ───────────────────────────────────────────────────────────────

def _anthropic_client(api_key: str = None, model_provider: str = None) -> Anthropic:
    base_url = _ANTHROPIC_BASE_URLS.get(model_provider or _DEFAULT_PROVIDER)
    return Anthropic(api_key=api_key or _DEFAULT_API_KEY, base_url=base_url)


# ── Gemini helpers ────────────────────────────────────────────────────────────

def _to_gemini_history(messages: list) -> tuple[list, str]:
    """
    Split the messages list into chat history (all but last) and the final user
    message. Converts Anthropic role names to Gemini role names.
    """
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
) -> str:
    client   = google_genai.Client(api_key=api_key)
    history, last_message = _to_gemini_history(messages)

    contents = [
        google_types.Content(
            role=m["role"],
            parts=[google_types.Part(text=m["parts"][0])],
        )
        for m in history
    ]
    contents.append(
        google_types.Content(
            role="user",
            parts=[google_types.Part(text=last_message)],
        )
    )

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
    return response.text


# ── Public interface ──────────────────────────────────────────────────────────

def call_glm(
    max_tokens, requirements, context, temperature, top_p,
    prev_messages=None, previous_output=None,
    api_key: str = None, model_name: str = None, model_provider: str = None,
):
    provider  = model_provider or _DEFAULT_PROVIDER
    temperature = float(temperature)
    top_p       = float(top_p)

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
        return _call_gemini_session(
            api_key or _DEFAULT_API_KEY,
            model_name or _DEFAULT_MODEL,
            requirements, messages, max_tokens, temperature, top_p,
        )

    response = _anthropic_client(api_key, provider).messages.create(
        model=model_name or _DEFAULT_MODEL,
        max_tokens=max_tokens, system=requirements,
        messages=messages, temperature=temperature, top_p=top_p,
    )
    return response.content[0].text


def call_glm_session(
    max_tokens, requirements, messages: list, temperature, top_p,
    api_key: str = None, model_name: str = None, model_provider: str = None,
):
    """
    Multi-turn chat dispatcher.
    Routes to the Gemini SDK or the Anthropic-compatible SDK based on model_provider.
    """
    provider    = model_provider or _DEFAULT_PROVIDER
    temperature = float(temperature)
    top_p       = float(top_p)

    if provider == "gemini":
        return _call_gemini_session(
            api_key or _DEFAULT_API_KEY,
            model_name or _DEFAULT_MODEL,
            requirements, messages, max_tokens, temperature, top_p,
        )

    response = _anthropic_client(api_key, provider).messages.create(
        model=model_name or _DEFAULT_MODEL,
        max_tokens=max_tokens, system=requirements,
        messages=messages, temperature=temperature, top_p=top_p,
    )
    return response.content[0].text
