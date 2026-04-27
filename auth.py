import os
import jwt
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

def create_token(data, exp_mins):
    payload = {**data}
    payload["exp"] = datetime.now(tz=timezone.utc) + timedelta(minutes=exp_mins)
    payload["iat"] = datetime.now(tz=timezone.utc)
    token = jwt.encode(payload=payload, key= JWT_SECRET_KEY, algorithm="HS256")
    return token

def create_access_token(user_id, role):
    data = {"user_id": user_id, "role": role}
    access_token = create_token(data, 3)
    return access_token

def create_refresh_token(user_id):
    data = {"user_id": user_id}
    refresh_token = create_token(data, 5)
    return refresh_token

def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
