def authenticate_user(username: str, password: str):
    # Replace this with real DB lookup later
    if username == "admin" and password == "password":
        return {"access_token": "fake-token-123", "token_type": "bearer"}
    else:
        return {"hahaha u ass"}
    return None