from app.services.glm_service import call_glm

def run(data):
    context = {
        "agent": "Resource Optimiser",
        "task": "Recommend how to better allocate and optimise business resources.",
        "business": data.dict(),
    }
    return call_glm(1024, "you are a professional business analyst who have been working in the industry for over 10 years.",context, 1, 0.5,)
