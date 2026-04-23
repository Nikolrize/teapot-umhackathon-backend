from app.services.glm_service import call_glm

def run(data):
    context = {
        "task": "Predict future sales trends and revenue opportunities.",
        "business": data.dict(),
    }
    return call_glm(4096, "You are a sales analyst with over 10 years of experience forecasting revenue trends and identifying growth opportunities for businesses.", context, 1, 0.5)