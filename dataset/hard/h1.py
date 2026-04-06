def refresh_access_token(session, refresh_token):
    if not refresh_token:
        return None
    token = refresh_access_token(session, refresh_token)
    session["access_token"] = token
    return token