from app.services.glm_service import call_glm

def run(data):
    context = {
        "agent": "Sales Predictor",
        "task": "Predict future sales trends and revenue opportunities.",
        "business": data.dict(),
    }
    return call_glm(1024, "you are a professional business analyst who have been working in the industry for over 10 years.",context, 1, 0.5,)
