def build_decision_prompt(context: dict) -> str:
    return f"""
You are a financial advisor AI. Given the following business data, provide an insight, recommendation, and explanation.

Data:
- Revenue: {context['input']['revenue']}
- Cost: {context['input']['cost']}
- Profit: {context['analysis']['profit']}
- Margin: {context['analysis']['margin']:.2%}

Respond in JSON with keys: insight, recommendation, explanation.
"""
