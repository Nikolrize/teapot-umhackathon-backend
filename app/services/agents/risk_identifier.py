from app.services.glm_service import call_glm

def run(data):
    context = {
        "task": "Identify financial, operational, and market risks facing the business.",
        "business": data.dict(),
    }
    return call_glm(4096, "You are a risk management specialist with over 10 years of experience identifying and mitigating financial, operational, and market risks.", context, 1, 0.5)