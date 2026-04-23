from app.services.glm_service import call_glm

def run(data):
    context = {
        "task": "Suggest actionable ways to increase profit margins and reduce unnecessary costs.",
        "business": data.dict(),
    }
    return call_glm(4096, "You are a financial advisor with over 10 years of experience improving profit margins and eliminating cost inefficiencies for businesses.", context, 1, 0.5)