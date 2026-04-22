from app.services.glm_service import call_glm

def run(data):
    context = {
        "agent": "Scenario Simulator",
        "task": "Simulate best-case, worst-case, and likely business scenarios.",
        "business": data.dict(),
    }
    return call_glm(4096, "you are a professional business analyst who have been working in the industry for over 10 years.",context, 1, 0.5)
