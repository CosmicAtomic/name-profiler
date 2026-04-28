from slowapi import Limiter
from slowapi.util import get_remote_address

# This instance is shared across the whole app
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
