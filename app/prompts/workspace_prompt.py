BUSINESS_TYPES = [
    "retail",
    "food & beverage",
    "services",
    "tech",
    "manufacturing",
    "other",
]

BUSINESS_MODES = [
    "online",
    "physical",
    "hybrid",
    "n/a",
]


def build_workspace_system_prompt(workspace: dict) -> str:
    mode = workspace.get("mode_of_business") or "n/a"

    return f"""You are a business advisor AI for a workspace called "{workspace['name']}".

Business Profile:
- Type of Business: {workspace['business_type']}
- Mode of Business: {mode}
- Expected Costs: {workspace['expected_costs']}
- Description: {workspace['brief_description']}

Always tailor every response, analysis, and recommendation strictly based on this business context.
Do not give generic advice — your answers must reflect the nature, scale, and goals of this specific business."""
