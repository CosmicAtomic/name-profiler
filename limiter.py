from slowapi import Limiter
from fastapi import Request


def get_real_ip(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


limiter = Limiter(key_func=get_real_ip, default_limits=["60/minute"])
