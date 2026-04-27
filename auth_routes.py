import os
import requests
import uuid6
import secrets, base64, hashlib
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, Refresh_Token
from auth import create_access_token, create_refresh_token, verify_token
from schemas import RefreshRequest
from dotenv import load_dotenv
load_dotenv()

pending_states = {}

CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
CALL_BACK_URL = "http://localhost:8000/auth/github/callback"

auth_router = APIRouter(prefix='/auth')

@auth_router.get('/github')
async def auth_github():
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

    pending_states[state] = code_verifier

    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={CALL_BACK_URL}"
        f"&code_challenge={code_challenge}"
        f"&scope=user:email"
        f"&state={state}"
        f"&code_challenge_method=S256"
    )
    return RedirectResponse(github_url)


@auth_router.get("/github/callback")
async def github_callback(code: str, state: str, db: Session = Depends(get_db)):
    code_verifier = pending_states.pop(state, None)
    if not code_verifier:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    token_url = "https://github.com/login/oauth/access_token"
    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": CALL_BACK_URL,
        "code_verifier": code_verifier
    }
    token_headers = {"Accept": "application/json"}
    
    token_resp = requests.post(token_url, data=token_data, headers=token_headers)
    token_json = token_resp.json()
    github_token = token_json.get("access_token")

    if not github_token:
        raise HTTPException(status_code=400, detail="Failed to retrieve GitHub token")
    
    user_resp = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {github_token}"}
    )
    github_user = user_resp.json()
    github_id = str(github_user.get("id"))

    user = db.query(User).filter(User.github_id == github_id).first()
    if user:
        user.last_login_at = datetime.now(timezone.utc)
    else:
        user = User(
            id = str(uuid6.uuid7()),
            github_id = github_id,
            username = github_user.get("login"),
            email = github_user.get("email"),
            avatar_url = github_user.get("avatar_url"),
            role = "analyst",
            last_login_at = datetime.now(timezone.utc),
            created_at = datetime.now(timezone.utc)
        )
        db.add(user)
    db.commit()

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    db_token = Refresh_Token(
        id=str(uuid6.uuid7()),
        token=refresh_token,
        user_id=user.id,
        is_used=False,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_token)
    db.commit()

    return JSONResponse({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "username": user.username
    })

@auth_router.post('/refresh')
async def auth_refresh(request_body: RefreshRequest, db: Session = Depends(get_db)):
    payload = verify_token(request_body.refresh_token)
    if not payload:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Token is expired or invalid"})
    
    stored_token = db.query(Refresh_Token).filter(Refresh_Token.token == request_body.refresh_token, Refresh_Token.is_used == False).first()
    if not stored_token:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Token is expired or invalid"})
    
    stored_token.is_used = True
    user = db.query(User).filter(User.id == payload["user_id"]).first()

    new_access_token = create_access_token(user.id, user.role)
    new_refresh_token = create_refresh_token(user.id)

    db_token = Refresh_Token(
        id=str(uuid6.uuid7()),
        token=new_refresh_token,
        user_id=user.id,
        is_used=False,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_token)
    db.commit()

    return JSONResponse(content={
        "status": "success",
        "access_token": new_access_token,
        "refresh_token": new_refresh_token
    })

@auth_router.post('/logout')
async def auth_logout(request_body: RefreshRequest, db: Session = Depends(get_db)):
    stored_token = db.query(Refresh_Token).filter(Refresh_Token.token == request_body.refresh_token).first()
    if not stored_token:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid token"})
    stored_token.is_used = True
    db.commit()
    return JSONResponse({"status": "success", "message": "Logged out"})

