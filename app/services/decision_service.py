# AI Logic
from app.services.analysis_service import basic_analysis
from app.services.glm_service import call_glm

def generate_decision(data):
    analysis = basic_analysis(data)

    context = {
        "input": data.dict(),
        "analysis": analysis
    }

    glm_result = call_glm(context)

    return {
        "analysis": analysis,
        "decision": glm_result
    }