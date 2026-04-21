from fastapi import APIRouter
from starlette.requests import Request  # Direct import often bypasses FastAPI's wrapper logic
from app.services.oauth_service import oauth
from fastapi.responses import RedirectResponse
from authlib.integrations.base_client.errors import MismatchingStateError
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/auth")

@router.get("/github/login")
async def github_login(request: Request):
    # SAFETY: Clear the session before starting a new login
    request.session.clear() 
    
    redirect_uri = "http://localhost:8000/auth/github/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/github/callback")
async def github_callback(request: Request):
    try:
        # 1. Exchange the temporary 'code' from GitHub for a 'token'
        token = await oauth.github.authorize_access_token(request)
        
        # 2. Use that token to fetch the actual user profile from GitHub's API
        resp = await oauth.github.get("user", token=token)
        user = resp.json()
        
        # 3. Successful login - you can now save this to your database or return it
        return {
            "status": "success",
            "provider": "github",
            "user": user
        }

    except MismatchingStateError:
        # SAFETY: Instead of a 500 error, show a helpful message and reset link
        return HTMLResponse(content="""
            <html>
                <body>
                    <h1>Session Mismatch (CSRF Warning)</h1>
                    <p>Your login session could not be verified. This happens if you stay on the login page too long or have old cookies.</p>
                    <div>
                        <a href="/auth/github/login">Try Again</a>
                        <p>Still having trouble? <a href="/auth/reset">Click here to clear all cookies</a></p>
                    </div>
                </body>
            </html>
        """, status_code=400)
    
    except Exception as e:
        # Catch other errors (like GitHub being down or invalid secrets)
        print(f"General OAuth Error: {str(e)}")
        return {"error": "An unexpected error occurred during login."}
    

@router.get("/google/login")
async def google_login(request: Request):
    # SAFETY: Clear the session before starting a new login
    request.session.clear() 
    
    redirect_uri = "http://localhost:8000/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user = token.get("userinfo")
        return {"provider": "google", "user": user}
    except MismatchingStateError:
        return HTMLResponse(content="""
            <html>
                <body>
                    <h1>Login Timeout or CSRF Warning</h1>
                    <p>Your session expired or was interrupted. Please clear your cookies and try again.</p>
                    <a href="/auth/google/login">Click here to try again</a>
                    <br><br>
                    <a href="/auth/reset">Click here to reset your connection</a>
                </body>
            </html>
        """, status_code=400)

@router.get("/reset")
async def reset_session(request: Request):
    """
    Clears the session cookie and redirects to the homepage.
    Tell users to go here if they see 'Mismatching State' errors.
    """
    request.session.clear()
    response = RedirectResponse(url="/")
    # This force-expires the cookie on the browser side too
    response.delete_cookie("fastapi_session") 
    return response