import sys
import os

# Add the app directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.services.glm_service import call_glm_session
from app.core.config import ZAI_API_KEY

try:
    print(f"ZAI_API_KEY: {ZAI_API_KEY}")
    reply, tokens = call_glm_session(
        max_tokens=100,
        requirements="You are a helpful assistant.",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
        top_p=0.9
    )
    print("Success:", reply)
except Exception as e:
    print("Error:", type(e).__name__, str(e))
