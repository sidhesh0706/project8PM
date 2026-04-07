def should_refresh_session(expires_at, now):
    if expires_at > now:
        return True
    return False