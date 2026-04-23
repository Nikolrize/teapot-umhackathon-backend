from app.core.config import ZAI_API_KEY
from anthropic import Anthropic
import json

client = Anthropic(
    api_key=ZAI_API_KEY,
    base_url="https://api.ilmu.ai/anthropic",
)

def call_glm(max_tokens, requirements, context, temperature, top_p, prev_messages=None, previous_output=None, reference: list = None):
    if isinstance(context, dict):
        task = context.get("task", "")
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
        context_str = context

    if prev_messages is None:
        response = client.messages.create(
            model="ilmu-glm-5.1",
            max_tokens=max_tokens,
            system=requirements,
            messages=[
                {"role": "user", "content": context_str}
            ],
            temperature=temperature,
            top_p=top_p,
        )
    else:
        prev_str = json.dumps(prev_messages) if isinstance(prev_messages, dict) else prev_messages
        prev_out_str = json.dumps(previous_output) if isinstance(previous_output, dict) else previous_output
        response = client.messages.create(
            model="ilmu-glm-5.1",
            max_tokens=max_tokens,
            system=requirements,
            messages=[
                {"role": "user", "content": prev_str},
                {"role": "assistant", "content": prev_out_str},
                {"role": "user", "content": context_str},
            ],
            temperature=temperature,
            top_p=top_p,
        )

    return response.content[0].text


def call_glm_session(max_tokens, requirements, messages: list, temperature, top_p):
    """Multi-turn version: accepts a full messages list built from session history."""
    response = client.messages.create(
        model="ilmu-glm-5.1",
        max_tokens=max_tokens,
        system=requirements,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
    )
    return response.content[0].text

