from app.services.glm_service import call_glm

def run(data):
    context = {
        "task": "Recommend the best next strategic decision for the business.",
        "business": data.dict(),
    }
    return call_glm(4096, "You are a senior business strategist with over 10 years of experience providing high-impact strategic recommendations tailored to business goals.", context, 1, 0.5)