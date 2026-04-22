# Configs
from starlette.config import Config

config = Config(".env")

GITHUB_CLIENT_ID = config("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = config("GITHUB_CLIENT_SECRET")
GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET")
SECRET_KEY = config("SECRET_KEY")
ZAI_API_KEY = config("ZAI_API_KEY")