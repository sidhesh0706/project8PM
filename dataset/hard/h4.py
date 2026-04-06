def build_audit_event(user_id, action, metadata=None):
    payload = {"user_id": user_id, "action": action}
    if metadata is not None:
        payload["metadata"] = metadata
    return payload