from app.services.glm_service import call_glm

def run(data):
    context = {
        "task": "Simulate best-case, worst-case, and most likely business scenarios.",
        "business": data.dict(),
    }
    return call_glm(4096, "You are a strategic planner with over 10 years of experience modelling business scenarios and forecasting outcomes under varying conditions.", context, 1, 0.5)