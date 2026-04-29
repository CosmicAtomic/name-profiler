from slowapi import Limiter
from fastapi import Request


def get_real_ip(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host


limiter = Limiter(key_func=get_real_ip, default_limits=["60/minute"], storage_uri="memory://")
