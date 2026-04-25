from app.services.glm_service import call_glm

def run(data):
    context = {
        "task": "Recommend how to better allocate and optimise business resources.",
        "business": data.dict(),
    }
    return call_glm(4096, "You are a resource management consultant with over 10 years of experience optimising staff, budget, and time allocation across businesses.", context, 1, 0.5)