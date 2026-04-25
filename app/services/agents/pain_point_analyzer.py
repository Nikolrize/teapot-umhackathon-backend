from app.services.glm_service import call_glm

def run(data):
    context = {
        "task": "Identify the key pain points and operational challenges facing the business.",
        "business": data.dict(),
    }
    return call_glm(4096, "You are an operations consultant with over 10 years of experience diagnosing business inefficiencies and operational challenges.", context, 1, 0.5)