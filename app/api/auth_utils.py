import os
from datetime import datetime, timedelta
from jose import jwt

# Move these to your .env file!
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-lab-key-123") 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # This generates the actual encrypted string
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt