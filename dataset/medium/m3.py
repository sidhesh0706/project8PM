def parse_webhook_event(payload):
    event_type = payload["type"]
    event_id = payload["id"]
    return {"type": event_type, "id": event_id}